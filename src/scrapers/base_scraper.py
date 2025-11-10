import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from src.utils import save_html


class BaseScraper(ABC):
    def __init__(self, url: str, file_name: str, scraper_settings: dict[str, Any]):
        self.url = url
        self.raw_html_path = os.path.join("html", f"{file_name}.html")
        self.json_path = os.path.join(
            "json" if not os.getenv("CI") else ".", f"{file_name}.json"
        )
        self.scraper_settings = scraper_settings

    def _fetch_html(self) -> Optional[BeautifulSoup]:
        retries = self.scraper_settings.get("retries", 3)
        delay = self.scraper_settings.get("delay", 5)
        timeout = self.scraper_settings.get("timeout", 15)

        for attempt in range(retries):
            print(f"Fetching HTML from {self.url} (Attempt {attempt + 1}/{retries})...", flush=True)
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
                    return None
        return None

    def save_to_json(self, data: dict[Any, Any] | list[Any]):
        json_dir = os.path.dirname(self.json_path)
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)

        print(f"Saving data to {self.json_path}...")
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {self.json_path}")

    @abstractmethod
    def parse(self, soup: BeautifulSoup) -> dict[Any, Any] | list[Any]:
        pass

    def run(self):
        soup = self._fetch_html()
        if soup:
            data = self.parse(soup)
            self.save_to_json(data)
        else:
            self.save_to_json({})
