import unittest

from src.validation import OutputValidationError, validate_scraper_output


class OutputValidationTests(unittest.TestCase):
    def test_rejects_empty_output(self) -> None:
        with self.assertRaises(OutputValidationError):
            validate_scraper_output("raid_bosses", {})

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

    def test_accepts_valid_events(self) -> None:
        validate_scraper_output(
            "events",
            {
                "Event": [
                    {
                        "title": "Working",
                        "article_url": "url",
                        "category": "Event",
                    }
                ]
            },
        )


if __name__ == "__main__":
    unittest.main()
