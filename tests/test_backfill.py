import unittest
from typing import Any
from unittest.mock import Mock, patch

import requests

from src.backfill import ArchiveBackfiller, modernize_details, modernize_pokemon


def archived_event(**overrides: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "title": "Legacy Event",
        "article_url": "https://example.invalid/events/legacy/",
        "banner_url": "banner-url",
        "category": "Event",
        "details": {"bonuses": ["2x Stardust"], "spawns": ["Zubat"]},
        "is_local_time": False,
        "start_time": 1,
        "end_time": 2,
    }
    event.update(overrides)
    return event


EVENT_PAGE = (
    '<div class="page-content"><div class="header-page">Title</div>'
    "<p>Recovered description.</p>"
    '<h2 class="event-section-header" id="spawns">Spawns</h2>'
    '<ul class="pkmn-list"><li class="pkmn-list-item">'
    '<div class="pkmn-name">Zubat</div>'
    '<div class="pkmn-list-img"><img src="zubat.png"></div>'
    "</li></ul></div>"
)


class ModernizeTests(unittest.TestCase):
    def test_converts_legacy_names_without_inventing_sprites(self) -> None:
        self.assertEqual(
            modernize_pokemon(["Zubat"]),
            [{"name": "Zubat", "asset_url": None, "shiny_available": False}],
        )

    def test_leaves_current_entries_untouched(self) -> None:
        entry = {"name": "Palkia", "asset_url": "palkia.png", "shiny_available": True}
        self.assertEqual(modernize_pokemon([entry]), [entry])

    def test_leaves_bonuses_as_plain_strings(self) -> None:
        details = modernize_details({"bonuses": ["2x XP"], "spawns": ["Zubat"]})
        self.assertEqual(details["bonuses"], ["2x XP"])
        self.assertEqual(details["spawns"][0]["name"], "Zubat")


class ArchiveBackfillerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backfiller = ArchiveBackfiller("owner", "repository", [2025], delay=0)

    @staticmethod
    def response(text: str = "", status_code: int = 200) -> Mock:
        response = Mock(spec=requests.Response)
        response.status_code = status_code
        response.text = text
        response.raise_for_status.return_value = None
        return response

    def test_recovers_description_and_sprites_from_a_live_page(self) -> None:
        event = archived_event()
        with patch("src.backfill.requests.get", return_value=self.response(EVENT_PAGE)):
            rebuilt, outcome = self.backfiller._backfill_event(event)

        self.assertEqual(outcome, "description recovered")
        self.assertEqual(rebuilt["description"], "Recovered description.")
        self.assertEqual(rebuilt["details"]["spawns"][0]["name"], "Zubat")
        self.assertTrue(rebuilt["details"]["spawns"][0]["asset_url"])

    def test_preserves_archived_identity_and_times(self) -> None:
        event = archived_event()
        with patch("src.backfill.requests.get", return_value=self.response(EVENT_PAGE)):
            rebuilt, _ = self.backfiller._backfill_event(event)

        for key in ("title", "category", "article_url", "banner_url", "start_time"):
            self.assertEqual(rebuilt[key], event[key])

    def test_missing_page_keeps_the_snapshot_and_only_modernizes_it(self) -> None:
        event = archived_event()
        with patch(
            "src.backfill.requests.get", return_value=self.response(status_code=404)
        ):
            rebuilt, outcome = self.backfiller._backfill_event(event)

        self.assertEqual(outcome, "missing")
        self.assertNotIn("description", rebuilt)
        self.assertEqual(
            rebuilt["details"]["spawns"],
            [{"name": "Zubat", "asset_url": None, "shiny_available": False}],
        )

    def test_existing_description_survives_a_page_without_one(self) -> None:
        event = archived_event(description="Original description.")
        page = '<div class="page-content"><div class="header-page">Title</div></div>'
        with patch("src.backfill.requests.get", return_value=self.response(page)):
            rebuilt, _ = self.backfiller._backfill_event(event)

        self.assertEqual(rebuilt["description"], "Original description.")

    def test_network_failures_are_not_silently_swallowed(self) -> None:
        from src.backfill import ArchiveBackfillError

        with patch(
            "src.backfill.requests.get",
            side_effect=requests.ConnectionError("temporary outage"),
        ):
            with self.assertRaises(ArchiveBackfillError):
                self.backfiller._backfill_event(archived_event())


if __name__ == "__main__":
    unittest.main()
