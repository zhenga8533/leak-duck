from abc import ABC, abstractmethod
from typing import Any

from bs4 import BeautifulSoup

from src.config import ScraperSettings
from src.fetch import get_with_retries
from src.paths import HTML_DIR, data_dir
from src.utils import save_html, write_json_atomic
from src.validation import validate_scraper_output


class BaseScraper(ABC):
    def __init__(self, url: str, file_name: str, settings: ScraperSettings):
        self.url = url
        self.file_name = file_name
        self.raw_html_path = HTML_DIR / f"{file_name}.html"
        self.json_path = data_dir() / f"{file_name}.json"
        self.settings = settings

    def _fetch_html(self) -> BeautifulSoup:
        response = get_with_retries(self.url, self.settings)
        save_html(response.text, self.raw_html_path)
        return BeautifulSoup(response.content, "lxml")

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
