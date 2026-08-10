import unittest
from typing import Any

from src.validation import (
    OutputValidationError,
    validate_archive_output,
    validate_scraper_output,
)


def event(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "title": "Working",
        "article_url": "url",
        "banner_url": "banner-url",
        "category": "Event",
        "description": "Event description.",
        "details": {},
        "is_local_time": False,
        "start_time": 1,
        "end_time": 2,
    }
    record.update(overrides)
    return record


class OutputValidationTests(unittest.TestCase):
    def test_rejects_empty_output(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output("raid_bosses", {})

    def test_rejects_output_with_only_empty_sections(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output(
                "raid_bosses", {"1-Star Raids": [], "5-Star Raids": []}
            )

    def test_rejects_event_error_entries(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output(
                "events",
                {
                    "Event": [
                        {
                            "title": "Broken",
                            "article_url": "url",
                            "category": "Event",
                            "error": "timeout",
                        }
                    ]
                },
            )

    def test_rejects_skeletal_events(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output(
                "events",
                {
                    "Event": [
                        {
                            "title": "Incomplete",
                            "article_url": "url",
                            "category": "Event",
                            "details": {},
                        }
                    ]
                },
            )

    def test_accepts_valid_events(self) -> None:
        validate_scraper_output(
            "events",
            {
                "Event": [
                    {
                        "title": "Working",
                        "article_url": "url",
                        "banner_url": "banner-url",
                        "category": "Event",
                        "description": "Event description.",
                        "details": {},
                        "is_local_time": False,
                        "start_time": 1,
                        "end_time": 2,
                    }
                ]
            },
        )

    def test_accepts_valid_local_time_events(self) -> None:
        validate_scraper_output(
            "events",
            {
                "Event": [
                    {
                        "title": "Working",
                        "article_url": "url",
                        "banner_url": "banner-url",
                        "category": "Event",
                        "description": "Event description.",
                        "details": {},
                        "is_local_time": True,
                        "start_time": "2026-07-20T10:00:00",
                        "end_time": "2026-07-20T11:00:00",
                    }
                ]
            },
        )

    def test_rejects_timezone_aware_local_time(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output(
                "events",
                {
                    "Event": [
                        {
                            "title": "Working",
                            "article_url": "url",
                            "banner_url": "banner-url",
                            "category": "Event",
                            "description": "Event description.",
                            "details": {},
                            "is_local_time": True,
                            "start_time": "2026-07-20T10:00:00-04:00",
                            "end_time": "2026-07-20T11:00:00-04:00",
                        }
                    ]
                },
            )

    def test_rejects_mismatched_event_category(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output(
                "events",
                {
                    "Raid Hour": [
                        {
                            "title": "Working",
                            "article_url": "url",
                            "banner_url": "banner-url",
                            "category": "Event",
                            "description": "Event description.",
                            "details": {},
                            "is_local_time": False,
                            "start_time": 1,
                            "end_time": 2,
                        }
                    ]
                },
            )

    def test_rejects_missing_description(self) -> None:
        record = event()
        del record["description"]
        with self.assertRaises(OutputValidationError):
            validate_scraper_output("events", {"Event": [record]})

    def test_rejects_blank_description(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output("events", {"Event": [event(description="   ")]})

    def test_rejects_invalid_details_section(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output(
                "events", {"Event": [event(details={"bonuses": "2x Stardust"})]}
            )


class ArchiveValidationTests(unittest.TestCase):
    def test_accepts_legacy_record_without_description(self) -> None:
        record = event()
        del record["description"]
        validate_archive_output("archive_2025", {"Event": [record]})

    def test_rejects_non_string_description(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_archive_output("archive_2025", {"Event": [event(description=42)]})

    def test_accepts_legacy_pokemon_strings(self) -> None:
        validate_archive_output(
            "archive_2025",
            {"Event": [event(details={"spawns": ["Zubat"], "bonuses": ["2x XP"]})]},
        )

    def test_accepts_current_pokemon_objects(self) -> None:
        validate_archive_output(
            "archive_2026",
            {
                "Event": [
                    event(
                        details={
                            "spawns": [
                                {
                                    "name": "Zubat",
                                    "asset_url": None,
                                    "shiny_available": True,
                                }
                            ]
                        }
                    )
                ]
            },
        )

    def test_rejects_unnamed_pokemon_object(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_archive_output(
                "archive_2026",
                {"Event": [event(details={"spawns": [{"asset_url": None}]})]},
            )

    def test_rejects_mismatched_category(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_archive_output("archive_2025", {"Raid Hour": [event()]})

    def test_rejects_invalid_time(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_archive_output("archive_2025", {"Event": [event(end_time="2")]})

    def test_rejects_missing_identity_fields(self) -> None:
        record = event()
        del record["article_url"]
        with self.assertRaises(OutputValidationError):
            validate_archive_output("archive_2025", {"Event": [record]})

    def test_allows_empty_archive_only_when_requested(self) -> None:
        validate_archive_output("archive_2027", {}, allow_empty=True)
        with self.assertRaises(OutputValidationError):
            validate_archive_output("archive_2027", {})


if __name__ == "__main__":
    unittest.main()
