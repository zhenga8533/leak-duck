import concurrent.futures
from functools import partial
from typing import Any, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup

from src.utils import clean_banner_url

from .base_scraper import BaseScraper
from .event_page_scraper import EventPageScraper


def scrape_single_event_page(url: str, scraper: EventPageScraper) -> Optional[Dict[str, Any]]:
    """Helper function to scrape a single event page with a shared scraper instance."""
    return scraper.scrape(url)


class EventScraper(BaseScraper):
    def __init__(
        self,
        url: str,
        file_name: str,
        scraper_settings: Dict[str, Any],
        check_existing_events: bool = False,
        github_user: Optional[str] = None,
        github_repo: Optional[str] = None,
    ):
        super().__init__(url, file_name, scraper_settings)
        self.check_existing_events = check_existing_events
        self.github_user = github_user
        self.github_repo = github_repo
        self.existing_event_urls: Set[str] = set()
        self.existing_events_data: Dict[str, List[Dict[str, Any]]] = {}
        if self.check_existing_events:
            self._fetch_existing_events()

    def _fetch_existing_events(self):
        if not self.github_user or not self.github_repo:
            print("GitHub user or repo not configured. Skipping check for existing events.")
            return

        data_url = f"https://raw.githubusercontent.com/{self.github_user}/{self.github_repo}/data/events.json"
        try:
            timeout = self.scraper_settings.get("timeout", 15)
            response = requests.get(data_url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            self.existing_events_data = data
            for category in data.values():
                for event in category:
                    self.existing_event_urls.add(event["article_url"])
            print(f"Found {len(self.existing_event_urls)} existing events.")
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Could not fetch existing events: {e}")
            self.existing_events_data = {}

    def parse(self, soup: BeautifulSoup) -> Dict[str, List[Dict[str, Any]]]:
        events_to_scrape: List[Dict[str, Any]] = []
        event_links = soup.select("a.event-item-link")

        for link in event_links:
            title_element = link.select_one("div.event-text h2")
            image_element = link.select_one(".event-img-wrapper img")
            category_element = link.select_one(".event-item-wrapper > p")

            if not title_element:
                continue

            article_url = "https://leekduck.com" + link["href"]

            if self.check_existing_events and article_url in self.existing_event_urls:
                continue

            events_to_scrape.append(
                {
                    "title": title_element.get_text(strip=True),
                    "article_url": article_url,
                    "banner_url": (
                        clean_banner_url(image_element["src"].strip())
                        if image_element and "src" in image_element.attrs
                        else None
                    ),
                    "category": category_element.get_text(strip=True) if category_element else "Event",
                }
            )

        all_events_data: Dict[str, Dict[str, Any]] = {event["article_url"]: event for event in events_to_scrape}

        if events_to_scrape:
            page_scraper = EventPageScraper()
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    urls_to_scrape = [event["article_url"] for event in events_to_scrape]
                    scrape_func = partial(scrape_single_event_page, scraper=page_scraper)
                    results = executor.map(scrape_func, urls_to_scrape)
                    for result in results:
                        if result and result.get("article_url") in all_events_data:
                            all_events_data[result["article_url"]].update(result)
            finally:
                page_scraper.close()

        new_events_by_category: Dict[str, List[Dict[str, Any]]] = {}
        for event in all_events_data.values():
            category = event["category"]
            if category not in new_events_by_category:
                new_events_by_category[category] = []
            new_events_by_category[category].append(event)

        merged_events = self.existing_events_data.copy()
        for category, events in new_events_by_category.items():
            if category not in merged_events:
                merged_events[category] = []
            merged_events[category].extend(events)

        return merged_events
