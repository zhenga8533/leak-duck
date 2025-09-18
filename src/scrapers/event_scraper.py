import concurrent.futures
import datetime
import re

import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class EventScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://leekduck.com/events/", "events")

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
                if next_element:
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
                if next_element:
                    for li in next_element.find_all("li", class_="pkmn-list-item"):
                        name_div = li.find("div", class_="pkmn-name")
                        if name_div:
                            shiny_pokemon.append(name_div.get_text(strip=True))
            event_details["shiny_pokemon"] = shiny_pokemon

            # Scrape event bonuses
            bonuses = []
            bonuses_header = soup.find("h2", string=re.compile(r"Event Bonuses", re.I))
            if bonuses_header:
                next_element = bonuses_header.find_next_sibling()
                if next_element and next_element.name == "ul":
                    for li in next_element.find_all("li"):
                        bonuses.append(li.get_text(strip=True))
            event_details["bonuses"] = bonuses

            return event_details

        except requests.exceptions.RequestException as e:
            print(f"Error fetching event page {url}: {e}")
            return {"article_url": url}  # Return the URL to merge data later

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
            # Create a list of URLs to scrape
            urls_to_scrape = [event["article_url"] for event in events_to_scrape]
            # Map the executor to the scraping function and URLs
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
