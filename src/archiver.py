import json
from datetime import datetime, timezone

import requests


class EventArchiver:
    def __init__(self, user, repo):
        base_url = f"https://raw.githubusercontent.com/{user}/{repo}/data"
        self.current_events_url = f"{base_url}/events.json"
        self.archive_url = f"{base_url}/archive.json"
        self.events_path = "events.json"
        self.archive_path = "archive.json"

    def run(self):
        print("--- Running Event Archiver ---")
        now_utc_timestamp = int(datetime.now(timezone.utc).timestamp())

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
                if not event.get("is_local_time") and event.get("end_time") and isinstance(event["end_time"], int):
                    if event["end_time"] < now_utc_timestamp:
                        print(f"Archiving '{event['title']}'...")

                        if category not in archive_data:
                            archive_data[category] = []
                        archive_data[category].append(event)
                        newly_archived_count += 1
                    else:
                        active_events_in_category.append(event)
                else:
                    active_events_in_category.append(event)

            if active_events_in_category:
                remaining_events[category] = active_events_in_category

        print(f"Archived {newly_archived_count} new event(s).")

        if newly_archived_count > 0:
            with open(self.archive_path, "w", encoding="utf-8") as f:
                json.dump(archive_data, f, ensure_ascii=False, indent=4)
            print("archive.json has been updated locally.")

            with open(self.events_path, "w", encoding="utf-8") as f:
                json.dump(remaining_events, f, ensure_ascii=False, indent=4)
            print("events.json has been cleaned of old events locally.")
