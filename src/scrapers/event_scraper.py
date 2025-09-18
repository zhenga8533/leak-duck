import concurrent.futures
import datetime
import re

import requests
from bs4 import BeautifulSoup, NavigableString

from .base_scraper import BaseScraper


class EventScraper(BaseScraper):
    def __init__(
        self, url, file_name, scraper_settings, check_existing_events=False, github_user=None, github_repo=None
    ):
        super().__init__(url, file_name, scraper_settings)
        self.check_existing_events = check_existing_events
        self.github_user = github_user
        self.github_repo = github_repo
        self.existing_event_urls = set()
        if self.check_existing_events:
            self._fetch_existing_events()

    def _fetch_existing_events(self):
        if not self.github_user or not self.github_repo:
            print("GitHub user or repo not configured. Skipping check for existing events.")
            return

        data_url = f"https://raw.githubusercontent.com/{self.github_user}/{self.github_repo}/data/events.json"
        try:
            response = requests.get(data_url, timeout=15)
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
        try:
            print(f"Scraping event page: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "lxml")

            event_details = {"article_url": url}
            content = soup.find("div", class_="page-content")
            if not content:
                return event_details

            # --- Data Extraction Logic ---

            # 1. Scrape Main Description
            description_div = content.find("div", class_="event-description")
            if description_div:
                description_texts = [p.get_text(strip=True) for p in description_div.find_all("p", recursive=False)]
                event_details["description"] = "\n".join(description_texts)

            # 2. Iterate Through Main Sections
            main_sections = content.find_all("h2", class_="event-section-header")
            for section in main_sections:
                section_id = section.get("id")
                if not section_id:
                    continue

                # Find all content between this header and the next main header
                next_element = section.find_next_sibling()
                while next_element and not (
                    next_element.name == "h2" and "event-section-header" in next_element.get("class", [])
                ):
                    # Scrape Pokémon Lists
                    if next_element.name == "ul" and "pkmn-list-flex" in next_element.get("class", []):
                        pokemon_list = set()
                        for li in next_element.find_all("li", class_="pkmn-list-item"):
                            name_div = li.find("div", class_="pkmn-name")
                            if name_div:
                                pokemon_list.add(name_div.get_text(strip=True))
                        if pokemon_list:
                            event_details.setdefault(section_id, []).extend(sorted(list(pokemon_list)))

                    # Scrape Bonus Lists
                    if next_element.name == "div" and "bonus-list" in next_element.get("class", []):
                        bonuses = set()
                        for item in next_element.find_all("div", class_="bonus-text"):
                            bonuses.add(item.get_text(strip=True).strip("*"))
                        if bonuses:
                            event_details.setdefault(section_id, []).extend(sorted(list(bonuses)))

                    next_element = next_element.find_next_sibling()

                # Clean up duplicates within the section
                if section_id in event_details:
                    event_details[section_id] = sorted(list(set(event_details[section_id])))

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

        if events_to_scrape:
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
