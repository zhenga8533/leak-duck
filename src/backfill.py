import argparse
import json
import time
from typing import Any, cast

import requests
from bs4 import BeautifulSoup

from src.paths import data_dir
from src.scrapers.event_page_scraper import EventPageScraper
from src.utils import write_json_atomic
from src.validation import validate_archive_output

POKEMON_DEFAULTS = {"asset_url": None, "shiny_available": False}


class ArchiveBackfillError(RuntimeError):
    """Raised when published archives cannot be safely rebuilt."""


def modernize_pokemon(entries: list[Any]) -> list[Any]:
    """Convert legacy Pokémon name strings into the current object format.

    Used for events whose source page no longer exists, so the name is all the
    archive can honestly claim; `asset_url` stays null rather than guessed.
    """
    return [
        {"name": entry, **POKEMON_DEFAULTS} if isinstance(entry, str) else entry
        for entry in entries
    ]


def modernize_details(details: dict[str, Any]) -> dict[str, Any]:
    return {
        section: entries
        if section == "bonuses" or not isinstance(entries, list)
        else modernize_pokemon(entries)
        for section, entries in details.items()
    }


class ArchiveBackfiller:
    """Rebuilds published archives from their original Leek Duck pages.

    Re-scraping is the only authoritative source for details that were never
    captured, so pages that still exist are re-read and pages that are gone are
    left as-is apart from a format conversion.
    """

    def __init__(self, user: str, repo: str, years: list[int], delay: float = 0.15):
        self.repo_base_url = f"https://raw.githubusercontent.com/{user}/{repo}/data"
        self.archives_dir = data_dir() / "archives"
        self.years = years
        self.delay = delay
        self.page_scraper = EventPageScraper({"timeout": 20})

    def _fetch_archive(self, year: int) -> dict[str, list[dict[str, Any]]]:
        url = f"{self.repo_base_url}/archives/archive_{year}.json"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            archive = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            raise ArchiveBackfillError(f"Could not fetch the {year} archive") from e

        if not isinstance(archive, dict):
            raise ArchiveBackfillError(f"Published {year} archive is not a JSON object")

        archive = cast(dict[str, list[dict[str, Any]]], archive)
        validate_archive_output(f"archive_{year}", archive, allow_empty=True)
        return archive

    def _rescrape(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Return the current page's parse, or None when the page is gone."""
        url = event["article_url"]
        response = requests.get(url, timeout=20)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        return self.page_scraper._parse_event_details(soup, url)

    def _backfill_event(self, event: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Return the rebuilt event and the outcome for reporting."""
        try:
            parsed = self._rescrape(event)
        except requests.exceptions.RequestException as e:
            raise ArchiveBackfillError(f"Could not read {event['article_url']}") from e

        if parsed is None:
            # The page is gone; keep the snapshot and only modernize its shape.
            return {**event, "details": modernize_details(event["details"])}, "missing"

        rebuilt = dict(event)
        if parsed.get("description"):
            rebuilt["description"] = parsed["description"]
        if parsed.get("details"):
            rebuilt["details"] = parsed["details"]
        rebuilt["details"] = modernize_details(rebuilt["details"])

        gained_description = "description" not in event and "description" in rebuilt
        changed = rebuilt != event
        if gained_description:
            return rebuilt, "description recovered"
        return rebuilt, "updated" if changed else "unchanged"

    def run(self, dry_run: bool = False) -> None:
        print("--- Running Archive Backfill ---", flush=True)
        for year in self.years:
            archive = self._fetch_archive(year)
            outcomes: dict[str, int] = {}
            gone: list[str] = []

            for category, events in archive.items():
                for index, event in enumerate(events):
                    rebuilt, outcome = self._backfill_event(event)
                    events[index] = rebuilt
                    outcomes[outcome] = outcomes.get(outcome, 0) + 1
                    if outcome == "missing":
                        gone.append(f"[{category}] {event['article_url']}")
                    time.sleep(self.delay)

            validate_archive_output(f"archive_{year}", archive)
            summary = ", ".join(f"{count} {name}" for name, count in outcomes.items())
            print(f"archive_{year}: {summary}", flush=True)
            for url in gone:
                print(f"   page no longer exists: {url}", flush=True)

            if dry_run:
                print(f"archive_{year}: dry run, nothing written.", flush=True)
                continue

            archive_path = self.archives_dir / f"archive_{year}.json"
            write_json_atomic(archive_path, archive)
            print(f"archive_{year}: written to {archive_path}.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild published event archives.")
    parser.add_argument("years", type=int, nargs="+", help="archive years to rebuild")
    parser.add_argument(
        "--dry-run", action="store_true", help="report changes without writing"
    )
    args = parser.parse_args()

    with open("src/config.json", encoding="utf-8") as f:
        github = json.load(f)["github"]

    backfiller = ArchiveBackfiller(github["user"], github["repo"], args.years)
    backfiller.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
