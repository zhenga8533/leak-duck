import concurrent.futures
import datetime
import re

import requests
from bs4 import BeautifulSoup, NavigableString

from .base_scraper import BaseScraper


class EventScraper(BaseScraper):
    def __init__(self, url, file_name, scraper_settings, check_existing_events=False):
        super().__init__(url, file_name, scraper_settings)
        self.check_existing_events = check_existing_events
        self.existing_event_urls = set()
        if self.check_existing_events:
            self._fetch_existing_events()

    def _fetch_existing_events(self):
        """
        Fetches the current events.json from the data branch to avoid re-scraping existing events.
        """
        url = "https://raw.githubusercontent.com/zhenga8533/leak-duck/data/events.json"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            for category in data.values():
                for event in category:
                    self.existing_event_urls.add(event["article_url"])
            print(f"Found {len(self.existing_event_urls)} existing events.")
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Could not fetch existing events: {e}")

    def _process_time_data(self, date_string, is_local):
        if not date_string or "calculating" in date_string.lower():
            return None
        try:
            if is_local:
                return date_string[:19]

            dt_object = datetime.datetime.fromisoformat(date_string)
            return int(dt_object.timestamp())
        except (ValueError, TypeError, IndexError):
            return None

    def _clean_banner_url(self, url):
        if not url:
            return None
        return re.sub(r"cdn-cgi/image/.*?\/(?=assets)", "", url)

    def _scrape_event_page(self, url):
        """
        Scrapes an individual event page for additional details.
        """
        try:
            print(f"Scraping event page: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "lxml")

            event_details = {"article_url": url}

            # Scrape raids
            raids = []
            raids_header = soup.find("h2", id="raids")
            if raids_header:
                next_element = raids_header.find_next_sibling("ul", class_="pkmn-list-flex")
                if next_element and not isinstance(next_element, NavigableString):
                    for li in next_element.find_all("li", class_="pkmn-list-item"):
                        name_div = li.find("div", class_="pkmn-name")
                        if name_div:
                            raids.append(name_div.get_text(strip=True))
            event_details["raids"] = raids

            # Scrape shiny pokemon
            shiny_pokemon = []
            shiny_header = soup.find("h2", id="shiny")
            if shiny_header:
                next_element = shiny_header.find_next_sibling("ul", class_="pkmn-list-flex")
                if next_element and not isinstance(next_element, NavigableString):
                    for li in next_element.find_all("li", class_="pkmn-list-item"):
                        name_div = li.find("div", class_="pkmn-name")
                        if name_div:
                            shiny_pokemon.append(name_div.get_text(strip=True))
            event_details["shiny_pokemon"] = shiny_pokemon

            # Scrape event bonuses
            bonuses = []
            bonuses_header = soup.find("h2", string=re.compile(r"Event Bonuses", re.I))
            if bonuses_header:
                next_element = bonuses_header.find_next_sibling("ul")
                if next_element and not isinstance(next_element, NavigableString):
                    for li in next_element.find_all("li"):
                        bonuses.append(li.get_text(strip=True))
            event_details["bonuses"] = bonuses

            return event_details

        except requests.exceptions.RequestException as e:
            print(f"Error fetching event page {url}: {e}")
            return {"article_url": url}

    def parse(self, soup):
        events_to_scrape = []
        event_links = soup.select("a.event-item-link")

        for link in event_links:
            wrapper = link.find_parent("span", class_="event-header-item-wrapper")
            time_period_element = wrapper.find("h5", class_="event-header-time-period") if wrapper else None
            title_element = link.select_one("div.event-text h2")
            image_element = link.select_one(".event-img-wrapper img")
            category_element = link.select_one(".event-item-wrapper > p")

            if not title_element:
                continue

            article_url = "https://leekduck.com" + link["href"]

            if self.check_existing_events and article_url in self.existing_event_urls:
                print(f"Skipping already scraped event: {article_url}")
                continue

            events_to_scrape.append(
                {
                    "title": title_element.get_text(strip=True),
                    "article_url": article_url,
                    "banner_url": (
                        self._clean_banner_url(image_element["src"].strip())
                        if image_element and "src" in image_element.attrs
                        else None
                    ),
                    "category": category_element.get_text(strip=True) if category_element else "Event",
                    "start_time": (
                        self._process_time_data(
                            time_period_element.get("data-event-start-date-check")
                            or time_period_element.get("data-event-start-date"),
                            time_period_element.get("data-event-local-time") == "true",
                        )
                        if time_period_element
                        else None
                    ),
                    "end_time": (
                        self._process_time_data(
                            time_period_element.get("data-event-end-date"),
                            time_period_element.get("data-event-local-time") == "true",
                        )
                        if time_period_element
                        else None
                    ),
                    "is_local_time": (
                        time_period_element.get("data-event-local-time") == "true" if time_period_element else False
                    ),
                }
            )

        all_events_data = {event["article_url"]: event for event in events_to_scrape}

        with concurrent.futures.ThreadPoolExecutor() as executor:
            urls_to_scrape = [event["article_url"] for event in events_to_scrape]
            results = executor.map(self._scrape_event_page, urls_to_scrape)
            for result in results:
                if result and result.get("article_url") in all_events_data:
                    all_events_data[result["article_url"]].update(result)

        events_by_category = {}
        for event in all_events_data.values():
            category = event["category"]
            if category not in events_by_category:
                events_by_category[category] = []
            events_by_category[category].append(event)

        return events_by_category
