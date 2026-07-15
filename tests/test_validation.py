import unittest

from src.validation import OutputValidationError, validate_scraper_output


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


if __name__ == "__main__":
    unittest.main()
