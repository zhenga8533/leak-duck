import json
import os
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup


class BaseScraper(ABC):
    def __init__(self, url, file_name):
        self.url = url
        self.raw_html_path = os.path.join("html", f"{file_name}.html")

        json_dir = "." if os.getenv("CI") else "json"
        if not os.path.exists(json_dir) and json_dir != ".":
            os.makedirs(json_dir)

        self.json_path = os.path.join(json_dir, f"{file_name}.json")

    def _fetch_html(self):
        print(f"Fetching HTML from {self.url}...")
        try:
            response = requests.get(self.url, timeout=15)
            response.raise_for_status()

            if not os.getenv("CI"):
                html_dir = os.path.dirname(self.raw_html_path)
                if not os.path.exists(html_dir):
                    os.makedirs(html_dir)
                with open(self.raw_html_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"Saved raw HTML to {self.raw_html_path}")

            return BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {self.url}: {e}")
            return None

    def save_to_json(self, data):
        if data is None or not data:
            print(f"No data to save for {self.json_path}.")
            return

        print(f"Saving data to {self.json_path}...")
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {self.json_path}")

    @abstractmethod
    def parse(self, soup) -> list | dict:
        pass

    def run(self):
        soup = self._fetch_html()
        if soup:
            data = self.parse(soup)
            self.save_to_json(data)
