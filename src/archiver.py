import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class EventArchiver:
    def __init__(self, user: str, repo: str):
        self.repo_base_url = f"https://raw.githubusercontent.com/{user}/{repo}/data"
        self.events_url = f"{self.repo_base_url}/events.json"

        self.json_dir = "." if os.getenv("CI") else "json"
        self.archives_dir = os.path.join(self.json_dir, "archives")

        if not os.path.exists(self.archives_dir):
            os.makedirs(self.archives_dir)

        self.events_path = os.path.join(self.json_dir, "events.json")

    def _should_archive(self, event: dict[str, Any], now_utc: datetime) -> tuple[bool, datetime | None]:
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
            end_dt_utc = datetime.fromtimestamp(end_time, tz=timezone.utc)
            if now_utc > end_dt_utc:
                return True, end_dt_utc

        return False, None

    def run(self):
        print("--- Running Event Archiver ---", flush=True)
        now_utc = datetime.now(timezone.utc)

        try:
            response = requests.get(self.events_url, timeout=15)
            response.raise_for_status()
            current_events_data = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Could not fetch events.json to archive. It may not exist yet. Error: {e}", flush=True)
            return

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

        if not events_to_archive_by_year:
            print("No new events to archive.", flush=True)
            return

        for year, events in events_to_archive_by_year.items():
            self._update_archive_file(year, events)

        with open(self.events_path, "w", encoding="utf-8") as f:
            json.dump(remaining_events, f, ensure_ascii=False, indent=4)
        print(f"events.json has been cleaned and saved to {self.events_path}.", flush=True)

    def _update_archive_file(self, year: int, events: list[dict[str, Any]]):
        archive_file_path = os.path.join(self.archives_dir, f"archive_{year}.json")
        archive_url = f"{self.repo_base_url}/archives/archive_{year}.json"

        try:
            response = requests.get(archive_url, timeout=15)
            response.raise_for_status()
            archive_data = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            archive_data = {}

        for event in events:
            category = event["category"]
            if category not in archive_data:
                archive_data[category] = []
            archive_data[category].append(event)

            # Simple de-duplication
            unique_events = list({e["article_url"]: e for e in archive_data[category]}.values())
            archive_data[category] = unique_events

        with open(archive_file_path, "w", encoding="utf-8") as f:
            json.dump(archive_data, f, ensure_ascii=False, indent=4)
        print(f"Archived {len(events)} event(s) to {archive_file_path}.", flush=True)
