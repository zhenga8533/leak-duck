import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from src.archiver import ArchiveFetchError, EventArchiver
from src.validation import OutputValidationError


def archived_event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        "title": "Ended",
        "article_url": "new",
        "banner_url": "banner-url",
        "category": "Event",
        "description": "Event description.",
        "details": {"bonuses": ["2x Stardust"]},
        "is_local_time": False,
        "start_time": 0,
        "end_time": 1,
    }
    event.update(overrides)
    return event


class EventArchiverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.output_dir = Path(self.temporary_directory.name)
        self.archiver = EventArchiver("owner", "repository")
        self.archiver.json_dir = self.output_dir
        self.archiver.archives_dir = self.output_dir / "archives"
        self.archiver.events_path = self.output_dir / "events.json"

    @staticmethod
    def response(data: object, status_code: int = 200) -> Mock:
        response = Mock(spec=requests.Response)
        response.status_code = status_code
        response.json.return_value = data
        response.raise_for_status.return_value = None
        return response

    def test_archive_fetch_failure_does_not_overwrite_existing_history(self) -> None:
        archive_path = self.archiver.archives_dir / "archive_1970.json"
        archive_path.parent.mkdir(parents=True)
        archive_path.write_text(
            '{"Historic": [{"article_url": "old"}]}', encoding="utf-8"
        )
        current_events = {
            "Event": [
                {
                    "title": "Ended",
                    "article_url": "new",
                    "category": "Event",
                    "end_time": 1,
                }
            ]
        }

        with patch(
            "src.archiver.requests.get",
            side_effect=[
                self.response(current_events),
                requests.ConnectionError("temporary outage"),
            ],
        ):
            with self.assertRaises(ArchiveFetchError):
                self.archiver.run()

        self.assertEqual(
            json.loads(archive_path.read_text(encoding="utf-8")),
            {"Historic": [{"article_url": "old"}]},
        )
        self.assertFalse(self.archiver.events_path.exists())

    def test_no_new_archives_still_seeds_cleaned_events_file(self) -> None:
        current_events = {
            "Event": [
                {
                    "title": "Upcoming",
                    "article_url": "future",
                    "category": "Event",
                    "end_time": 4_102_444_800,
                }
            ]
        }
        with patch(
            "src.archiver.requests.get", return_value=self.response(current_events)
        ):
            self.archiver.run()

        self.assertEqual(
            json.loads(self.archiver.events_path.read_text(encoding="utf-8")),
            current_events,
        )

    def test_missing_archive_is_initialized_without_hiding_other_http_errors(
        self,
    ) -> None:
        current_events = {"Event": [archived_event()]}
        missing_archive_response = self.response({}, status_code=404)
        missing_archive_response.raise_for_status.side_effect = requests.HTTPError(
            response=missing_archive_response
        )

        with patch(
            "src.archiver.requests.get",
            side_effect=[
                self.response(current_events),
                missing_archive_response,
            ],
        ):
            self.archiver.run()

        archive_path = self.archiver.archives_dir / "archive_1970.json"
        self.assertEqual(
            json.loads(archive_path.read_text(encoding="utf-8")), current_events
        )

    def test_legacy_archive_without_description_is_preserved(self) -> None:
        legacy_event = archived_event(article_url="legacy")
        del legacy_event["description"]
        legacy_event["details"] = {"spawns": ["Zubat"]}
        published_archive = {"Event": [legacy_event]}
        current_events = {"Event": [archived_event()]}

        with patch(
            "src.archiver.requests.get",
            side_effect=[
                self.response(current_events),
                self.response(published_archive),
            ],
        ):
            self.archiver.run()

        archive_path = self.archiver.archives_dir / "archive_1970.json"
        self.assertEqual(
            json.loads(archive_path.read_text(encoding="utf-8")),
            {"Event": [legacy_event, archived_event()]},
        )

    def test_malformed_published_archive_is_not_overwritten(self) -> None:
        archive_path = self.archiver.archives_dir / "archive_1970.json"
        archive_path.parent.mkdir(parents=True)
        archive_path.write_text('{"Event": []}', encoding="utf-8")
        published_archive = {"Event": [archived_event(description=42)]}

        with patch(
            "src.archiver.requests.get",
            side_effect=[
                self.response({"Event": [archived_event()]}),
                self.response(published_archive),
            ],
        ):
            with self.assertRaises(OutputValidationError):
                self.archiver.run()

        self.assertEqual(
            json.loads(archive_path.read_text(encoding="utf-8")), {"Event": []}
        )
        self.assertFalse(self.archiver.events_path.exists())


if __name__ == "__main__":
    unittest.main()
