import json
import os
from datetime import datetime, timedelta, timezone

import requests


class EventArchiver:
    def __init__(self, user, repo):
        base_url = f"https://raw.githubusercontent.com/{user}/{repo}/data"
        self.current_events_url = f"{base_url}/events.json"
        self.archive_url = f"{base_url}/archive.json"

        # Determine save directory based on environment
        json_dir = "." if os.getenv("CI") else "json"
        if not os.path.exists(json_dir) and json_dir != ".":
            os.makedirs(json_dir)

        self.events_path = os.path.join(json_dir, "events.json")
        self.archive_path = os.path.join(json_dir, "archive.json")

    def run(self):
        print("--- Running Event Archiver ---")
        now_utc = datetime.now(timezone.utc)

        try:
            response = requests.get(self.current_events_url)
            response.raise_for_status()
            current_events_data = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"Could not fetch current events.json to archive. It may not exist yet. Error: {e}")
            return

        try:
            response = requests.get(self.archive_url)
            response.raise_for_status()
            archive_data = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            print("Could not fetch archive.json. A new one will be created.")
            archive_data = {}

        newly_archived_count = 0
        remaining_events = {}

        for category, events in current_events_data.items():
            active_events_in_category = []

            for event in events:
                should_archive = False
                end_time = event.get("end_time")

                if event.get("is_local_time") and isinstance(end_time, str):
                    # If local time, assume the last timezone offset (-12)
                    try:
                        naive_end_dt = datetime.fromisoformat(end_time)
                        last_tz_offset = timedelta(hours=-12)
                        last_tz = timezone(last_tz_offset)
                        absolute_end_dt = naive_end_dt.replace(tzinfo=last_tz)

                        if now_utc > absolute_end_dt:
                            should_archive = True
                    except ValueError:
                        pass
                elif isinstance(end_time, int):
                    if end_time < now_utc.timestamp():
                        should_archive = True

                if should_archive:
                    print(f"Archiving '{event['title']}'...")
                    if category not in archive_data:
                        archive_data[category] = []
                    archive_data[category].append(event)
                    newly_archived_count += 1
                else:
                    active_events_in_category.append(event)

            if active_events_in_category:
                remaining_events[category] = active_events_in_category

        print(f"Archived {newly_archived_count} new event(s).")

        if newly_archived_count > 0:
            with open(self.archive_path, "w", encoding="utf-8") as f:
                json.dump(archive_data, f, ensure_ascii=False, indent=4)
            print(f"archive.json has been updated locally at {self.archive_path}.")

            with open(self.events_path, "w", encoding="utf-8") as f:
                json.dump(remaining_events, f, ensure_ascii=False, indent=4)
            print(f"events.json has been cleaned of old events locally at {self.events_path}.")


if __name__ == "__main__":
    archiver = EventArchiver(user="zhenga8533", repo="leak-duck")
    archiver.run()
