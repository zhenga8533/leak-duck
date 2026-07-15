import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast

import requests

from src.paths import data_dir
from src.utils import write_json_atomic


class ArchiveFetchError(RuntimeError):
    """Raised when existing published data cannot be safely retrieved."""


class EventArchiver:
    def __init__(self, user: str, repo: str):
        self.repo_base_url = f"https://raw.githubusercontent.com/{user}/{repo}/data"
        self.events_url = f"{self.repo_base_url}/events.json"

        self.json_dir = data_dir()
        self.archives_dir = self.json_dir / "archives"
        self.events_path = self.json_dir / "events.json"

    def _should_archive(
        self, event: dict[str, Any], now_utc: datetime
    ) -> tuple[bool, datetime | None]:
        end_time = event.get("end_time")
        if not end_time:
            return False, None

        if event.get("is_local_time") and isinstance(end_time, str):
            try:
                naive_end_dt = datetime.fromisoformat(end_time)
                # Assume the event has ended if the current UTC time is past the event's end time in the last possible timezone (UTC-12)
                last_tz_offset = timedelta(hours=-12)
                absolute_end_dt = naive_end_dt.replace(tzinfo=timezone(last_tz_offset))
                if now_utc > absolute_end_dt:
                    return True, naive_end_dt
            except ValueError:
                return False, None
        elif isinstance(end_time, int):
            end_dt_utc = datetime.fromtimestamp(end_time, tz=UTC)
            if now_utc > end_dt_utc:
                return True, end_dt_utc

        return False, None

    def run(self) -> None:
        print("--- Running Event Archiver ---", flush=True)
        now_utc = datetime.now(UTC)

        try:
            response = requests.get(self.events_url, timeout=15)
            response.raise_for_status()
            current_events_data = response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                print(
                    "No published events.json exists yet; skipping archiving.",
                    flush=True,
                )
                return
            raise ArchiveFetchError("Could not fetch published events.json") from e
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            raise ArchiveFetchError("Could not fetch published events.json") from e

        if not isinstance(current_events_data, dict):
            raise ArchiveFetchError("Published events.json is not a JSON object")

        events_to_archive_by_year: dict[int, list[dict[str, Any]]] = {}
        remaining_events: dict[str, list[dict[str, Any]]] = {}

        for category, events in current_events_data.items():
            active_events_in_category = []
            for event in events:
                should_archive, end_dt = self._should_archive(event, now_utc)
                if should_archive and end_dt:
                    year = end_dt.year
                    if year not in events_to_archive_by_year:
                        events_to_archive_by_year[year] = []
                    events_to_archive_by_year[year].append(event)
                else:
                    active_events_in_category.append(event)

            if active_events_in_category:
                remaining_events[category] = active_events_in_category

        for year, events in events_to_archive_by_year.items():
            self._update_archive_file(year, events)

        write_json_atomic(self.events_path, remaining_events)
        if events_to_archive_by_year:
            print(
                f"events.json has been cleaned and saved to {self.events_path}.",
                flush=True,
            )
        else:
            print("No new events to archive.", flush=True)

    def _update_archive_file(self, year: int, events: list[dict[str, Any]]) -> None:
        archive_file_path = self.archives_dir / f"archive_{year}.json"
        archive_url = f"{self.repo_base_url}/archives/archive_{year}.json"

        try:
            response = requests.get(archive_url, timeout=15)
            response.raise_for_status()
            archive_data = response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                archive_data = {}
            else:
                raise ArchiveFetchError(
                    f"Could not safely fetch the {year} archive"
                ) from e
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            raise ArchiveFetchError(f"Could not safely fetch the {year} archive") from e

        if not isinstance(archive_data, dict):
            raise ArchiveFetchError(f"Published {year} archive is not a JSON object")
        archive_data = cast(dict[str, list[dict[str, Any]]], archive_data)

        for event in events:
            category = event["category"]
            if category not in archive_data:
                archive_data[category] = []
            archive_data[category].append(event)

            # Simple de-duplication
            unique_events = list(
                {e["article_url"]: e for e in archive_data[category]}.values()
            )
            archive_data[category] = unique_events

        write_json_atomic(archive_file_path, archive_data)
        print(f"Archived {len(events)} event(s) to {archive_file_path}.", flush=True)
