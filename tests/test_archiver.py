import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from src.archiver import ArchiveFetchError, EventArchiver


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


if __name__ == "__main__":
    unittest.main()
