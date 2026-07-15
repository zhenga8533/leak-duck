import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.paths import HTML_DIR, data_dir
from src.utils import save_html, write_json_atomic
from src.validation import validate_scraper_output


class ScraperFetchError(RuntimeError):
    """Raised after a scraper exhausts its HTTP retries."""


class BaseScraper(ABC):
    def __init__(self, url: str, file_name: str, scraper_settings: dict[str, Any]):
        self.url = url
        self.file_name = file_name
        self.raw_html_path = HTML_DIR / f"{file_name}.html"
        self.json_path = data_dir() / f"{file_name}.json"
        self.scraper_settings = scraper_settings

    def _fetch_html(self) -> BeautifulSoup:
        retries = self.scraper_settings.get("retries", 3)
        delay = self.scraper_settings.get("delay", 5)
        timeout = self.scraper_settings.get("timeout", 15)

        for attempt in range(retries):
            print(
                f"Fetching HTML from {self.url} (Attempt {attempt + 1}/{retries})...",
                flush=True,
            )
            try:
                response = requests.get(self.url, timeout=timeout)
                response.raise_for_status()

                save_html(response.text, self.raw_html_path)

                return BeautifulSoup(response.content, "lxml")
            except requests.exceptions.RequestException as e:
                print(f"Error fetching {self.url}: {e}", flush=True)
                if attempt < retries - 1:
                    print(f"Retrying in {delay} seconds...", flush=True)
                    time.sleep(delay)
                else:
                    print("All retry attempts failed.", flush=True)
                    raise ScraperFetchError(
                        f"Failed to fetch {self.url} after {retries} attempts"
                    ) from e
        raise ScraperFetchError(f"No fetch attempts configured for {self.url}")

    def save_to_json(self, data: dict[Any, Any] | list[Any]) -> None:
        print(f"Saving data to {self.json_path}...")
        write_json_atomic(self.json_path, data)
        print(f"Successfully saved {self.json_path}")

    @abstractmethod
    def parse(self, soup: BeautifulSoup) -> dict[Any, Any] | list[Any]:
        pass

    def run(self) -> None:
        soup = self._fetch_html()
        data = self.parse(soup)
        validate_scraper_output(self.file_name, data)
        self.save_to_json(data)
