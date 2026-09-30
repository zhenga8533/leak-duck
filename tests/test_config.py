import unittest

from src.config import PublishedData, load_config


class ConfigTests(unittest.TestCase):
    def test_bundled_config_loads(self) -> None:
        config = load_config()
        self.assertIn("EventScraper", config.scrapers)
        self.assertGreater(config.settings.retries, 0)

    def test_published_data_url(self) -> None:
        published = PublishedData("owner", "repository")
        self.assertEqual(
            published.url("archives/archive_2026.json"),
            "https://raw.githubusercontent.com/owner/repository/data/archives/archive_2026.json",
        )


if __name__ == "__main__":
    unittest.main()
