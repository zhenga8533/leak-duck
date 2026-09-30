from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast

import requests

from src.config import PublishedData
from src.fetch import get_if_exists
from src.paths import data_dir
from src.utils import write_json_atomic
from src.validation import validate_archive_output


class ArchiveFetchError(RuntimeError):
    """Raised when existing published data cannot be safely retrieved."""


class EventArchiver:
    def __init__(self, published: PublishedData):
        self.published = published
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

    def _fetch_published_json(self, path: str) -> Any | None:
        """Returns published JSON, or None when it has not been published yet."""
        try:
            response = get_if_exists(self.published.url(path), timeout=15)
            return response.json() if response is not None else None
        except (requests.exceptions.RequestException, ValueError) as e:
            raise ArchiveFetchError(f"Could not fetch published {path}") from e

    def run(self) -> None:
        print("--- Running Event Archiver ---", flush=True)
        now_utc = datetime.now(UTC)

        current_events_data = self._fetch_published_json("events.json")
        if current_events_data is None:
            print(
                "No published events.json exists yet; skipping archiving.", flush=True
            )
            return

        if not isinstance(current_events_data, dict):
            raise ArchiveFetchError("Published events.json is not a JSON object")

        events_to_archive_by_year: dict[int, list[dict[str, Any]]] = {}
        remaining_events: dict[str, list[dict[str, Any]]] = {}

        for category, events in current_events_data.items():
            active_events_in_category = []
            for event in events:
                should_archive, end_dt = self._should_archive(event, now_utc)
                if should_archive and end_dt:
                    events_to_archive_by_year.setdefault(end_dt.year, []).append(event)
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
        archive_name = f"archive_{year}"
        archive_file_path = self.archives_dir / f"{archive_name}.json"
        archive_data = self._fetch_published_json(f"archives/{archive_name}.json")
        if archive_data is None:
            archive_data = {}

        if not isinstance(archive_data, dict):
            raise ArchiveFetchError(f"Published {year} archive is not a JSON object")
        archive_data = cast(dict[str, list[dict[str, Any]]], archive_data)
        validate_archive_output(archive_name, archive_data, allow_empty=True)

        for event in events:
            archive_data.setdefault(event["category"], []).append(event)

        # A re-archived event replaces its earlier copy but keeps its position.
        for category in {event["category"] for event in events}:
            archive_data[category] = list(
                {e["article_url"]: e for e in archive_data[category]}.values()
            )

        validate_archive_output(archive_name, archive_data)
        write_json_atomic(archive_file_path, archive_data)
        print(f"Archived {len(events)} event(s) to {archive_file_path}.", flush=True)
