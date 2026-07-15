import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper, ScraperFetchError
from src.scrapers.egg_scraper import EggScraper
from src.scrapers.event_page_scraper import EventPageScraper
from src.scrapers.event_scraper import EventScraper
from src.scrapers.raid_boss_scraper import RaidBossScraper
from src.scrapers.research_scraper import ResearchScraper
from src.scrapers.rocket_lineup_scraper import RocketLineupScraper


class DummyScraper(BaseScraper):
    def parse(self, soup: BeautifulSoup) -> dict[str, list[object]]:
        return {"items": []}


class ScraperSafetyTests(unittest.TestCase):
    def test_fetch_failure_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "data.json"
            output_path.write_text('{"existing": true}', encoding="utf-8")
            scraper = DummyScraper(
                "https://example.invalid", "dummy", {"retries": 1, "delay": 0}
            )
            scraper.json_path = output_path

            with patch(
                "src.scrapers.base_scraper.requests.get",
                side_effect=requests.ConnectionError("offline"),
            ):
                with self.assertRaises(ScraperFetchError):
                    scraper.run()

            self.assertEqual(
                output_path.read_text(encoding="utf-8"), '{"existing": true}'
            )

    def test_existing_event_check_prefers_archiver_cleaned_local_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            events = {
                "Event": [
                    {
                        "title": "Active",
                        "article_url": "active-url",
                        "category": "Event",
                    }
                ]
            }
            (output_dir / "events.json").write_text(
                json.dumps(events), encoding="utf-8"
            )
            scraper = EventScraper.__new__(EventScraper)
            scraper.github_user = "owner"
            scraper.github_repo = "repository"
            scraper.scraper_settings = {"timeout": 1}
            scraper.existing_event_urls = set()
            scraper.existing_events_data = {}

            with patch("src.scrapers.event_scraper.data_dir", return_value=output_dir):
                scraper._fetch_existing_events()

            self.assertEqual(scraper.existing_events_data, events)
            self.assertEqual(scraper.existing_event_urls, {"active-url"})


class ParserFixtureTests(unittest.TestCase):
    settings = {"retries": 1, "delay": 0, "timeout": 1}

    def test_egg_parser(self) -> None:
        soup = BeautifulSoup(
            '<article class="article-page"><h2>5 km Eggs</h2><ul class="egg-grid">'
            '<li class="pokemon-card"><span class="name">Pikachu</span>'
            '<img class="pokemon-image" src="pikachu.png"><div class="rarity">'
            '<svg class="mini-egg"></svg></div></li></ul></article>',
            "lxml",
        )
        data = EggScraper("offline", "egg_pool", self.settings).parse(soup)
        self.assertEqual(data["5 km Eggs"][0]["hatch_distance"], 5)
        self.assertEqual(data["5 km Eggs"][0]["rarity_tier"], 1)

    def test_raid_parser(self) -> None:
        soup = BeautifulSoup(
            '<div class="raid-bosses"><div class="tier"><h2 class="header">Tier 5</h2>'
            '<div class="card"><p class="name">Mewtwo</p><div class="cp-range">2200 - 2300</div>'
            '<div class="boss-type"><div class="type"><img title="Psychic"></div></div>'
            '<img class="pokemon-image" src="mewtwo.png"></div></div></div>',
            "lxml",
        )
        data = RaidBossScraper("offline", "raid_bosses", self.settings).parse(soup)
        self.assertEqual(data["Tier 5"][0]["cp_range"], {"min": 2200, "max": 2300})

    def test_research_parser(self) -> None:
        soup = BeautifulSoup(
            '<div class="task-category"><h2>Catch</h2><li class="task-item">'
            '<span class="task-text">Catch one</span><ul class="reward-list">'
            '<li class="reward" data-reward-type="item"><span class="reward-label">Ball ×3</span>'
            '<div class="quantity">×3</div></li></ul></li></div>',
            "lxml",
        )
        data = ResearchScraper("offline", "research_tasks", self.settings).parse(soup)
        self.assertEqual(data["Catch"][0]["rewards"][0]["quantity"], 3)

    def test_rocket_parser(self) -> None:
        soup = BeautifulSoup(
            '<div class="rocket-profile"><div class="name">Leader</div><div class="lineup-info">'
            '<div class="slot encounter"><div class="pokemon-card" data-pokemon="Dratini">'
            '<img class="pokemon-image" src="dratini.png"></div></div></div></div>',
            "lxml",
        )
        data = RocketLineupScraper("offline", "rocket_lineups", self.settings).parse(
            soup
        )
        self.assertTrue(data["Leader"][0]["is_encounter"])

    def test_event_page_parser(self) -> None:
        soup = BeautifulSoup(
            '<div class="page-content"><span id="event-date-start">Monday July 20, 2026</span>'
            '<span id="event-time-start">at 10:00 AM Local Time</span>'
            '<span id="event-date-end">Monday July 20, 2026</span>'
            '<span id="event-time-end">at 11:00 AM Local Time</span>'
            '<div class="event-description"><p>Event description.</p></div>'
            '<h2 class="event-section-header" id="bonuses">Bonuses</h2>'
            '<div class="bonus-list"><div class="bonus-text">Double XP</div></div></div>',
            "lxml",
        )
        data = EventPageScraper(self.settings)._parse_event_details(soup, "event-url")
        self.assertEqual(data["start_time"], "2026-07-20T10:00:00")
        self.assertEqual(data["details"]["bonuses"], ["Double XP"])


if __name__ == "__main__":
    unittest.main()
