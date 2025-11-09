import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils import process_time_data, save_html


def clean_spacing(text: str) -> str:
    """
    Cleans up extra spaces around punctuation marks.

    Args:
        text: The text to clean.

    Returns:
        The cleaned text with proper spacing around punctuation.
    """
    # Remove spaces before punctuation marks
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    # Remove spaces after opening parentheses/brackets
    text = re.sub(r'([\(\[])\s+', r'\1', text)
    # Remove spaces before closing parentheses/brackets
    text = re.sub(r'\s+([\)\]])', r'\1', text)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


class EventPageScraper:
    """
    A class to scrape dynamic event pages using Selenium and BeautifulSoup.

    This scraper is designed to fetch and parse event details from pages that
    load their content dynamically using JavaScript.
    """

    def __init__(self):
        """Initializes the EventPageScraper and its WebDriver."""
        self.driver: WebDriver = self._get_driver()
        self.cache_expiration_hours = self._load_cache_expiration()
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def _get_driver(self) -> WebDriver:
        """Configures and returns a headless Chrome WebDriver instance."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # This will make the driver wait for the initial HTML to load, but not for all
        # resources like images and stylesheets. This can prevent the scraper from
        # getting stuck on pages with slow-loading assets.
        options.page_load_strategy = "eager"

        service = Service(log_output=os.devnull)
        return webdriver.Chrome(service=service, options=options)

    def _load_cache_expiration(self) -> int:
        """Loads the cache expiration time from config.json."""
        try:
            config_path = os.path.join("src", "config.json")
            with open(config_path, "r") as f:
                config = json.load(f)
                return config.get("scraper_settings", {}).get(
                    "cache_expiration_hours", 1
                )
        except Exception:
            return 1  # Default to 1 hour if config can't be loaded

    def _is_cache_valid(self, cache_path: str) -> bool:
        """Checks if the cached HTML file exists and is not expired."""
        if not os.path.exists(cache_path):
            return False

        file_modified_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        expiration_time = datetime.now() - timedelta(hours=self.cache_expiration_hours)

        return file_modified_time > expiration_time

    def _is_valid_time(self, time_value: Optional[Any]) -> bool:
        """Checks if a time value is valid (not None, empty, or invalid)."""
        if time_value is None or time_value == "":
            return False
        if isinstance(time_value, str):
            # Check for common invalid patterns
            if time_value.lower() in ["none", "null", "invalid", "tbd", "tba"]:
                return False
        return True

    def _has_valid_times(self, event_details: Dict[str, Any]) -> bool:
        """Checks if event has both valid start and end times."""
        return (
            self._is_valid_time(event_details.get("start_time"))
            and self._is_valid_time(event_details.get("end_time"))
        )

    def _fetch_dynamic_html(self, url: str) -> str:
        """Fetches the HTML content of a page after dynamic content has loaded."""
        # This will raise a TimeoutException if the page takes more than 20 seconds to load
        self.driver.set_page_load_timeout(20)
        self.driver.get(url)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#event-time-date-box span[data-event-page-date], "
                    "#event-time-date-box span:not([data-event-page-date])",
                )
            )
        )
        return self.driver.page_source

    def close(self) -> None:
        """Closes the WebDriver session."""
        self.driver.quit()

    def _parse_event_details(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parses the HTML soup to extract event details."""
        event_details: Dict[str, Any] = {"article_url": url, "details": {}}
        content = soup.find("div", class_="page-content")

        if not isinstance(content, Tag):
            return event_details

        # Time details
        start_date_element = soup.find("span", id="event-date-start")
        start_time_element = soup.find("span", id="event-time-start")
        end_date_element = soup.find("span", id="event-date-end")
        end_time_element = soup.find("span", id="event-time-end")

        is_local = not (
            isinstance(start_date_element, Tag)
            and "data-event-page-date" in start_date_element.attrs
        )
        event_details["is_local_time"] = is_local

        event_details["start_time"] = process_time_data(
            start_date_element, start_time_element, is_local
        )
        event_details["end_time"] = process_time_data(
            end_date_element, end_time_element, is_local
        )

        # Description and embedded sections
        description_div = content.find("div", class_="event-description")
        if isinstance(description_div, Tag):
            description_parts = []
            current_section_id: Optional[str] = None
            current_section_items = []

            for child in description_div.children:
                if not isinstance(child, Tag):
                    continue

                # Check if this is a section header (h2 with id)
                section_id_val = child.get("id")
                if child.name == "h2" and section_id_val and isinstance(section_id_val, str):
                    # Save current section if we were in one
                    if current_section_id and current_section_items:
                        event_details["details"][current_section_id] = current_section_items
                        current_section_items = []

                    # Start new section
                    current_section_id = section_id_val
                    continue

                # If we're in a section, collect items
                if current_section_id:
                    if child.name == "p":
                        text = clean_spacing(child.get_text(separator=" ", strip=True))
                        if text:
                            current_section_items.append(text)
                    elif child.name == "ul":
                        for li in child.find_all("li", recursive=False):
                            text = clean_spacing(li.get_text(separator=" ", strip=True))
                            if text:
                                current_section_items.append(text)
                # Otherwise, add to description
                else:
                    if child.name == "p":
                        text = clean_spacing(child.get_text(separator=" ", strip=True))
                        if text:
                            description_parts.append(text)
                    elif child.name == "ul":
                        for li in child.find_all("li", recursive=False):
                            text = clean_spacing(li.get_text(separator=" ", strip=True))
                            if text:
                                description_parts.append(f"- {text}")

            # Save any remaining section
            if current_section_id and current_section_items:
                event_details["details"][current_section_id] = current_section_items

            if description_parts:
                event_details["description"] = "\n".join(description_parts)

        # Main sections
        main_sections = content.find_all("h2", class_="event-section-header")
        for section in main_sections:
            self._parse_section(section, event_details)

        # Final cleanup - move bonuses to details if it exists
        if "bonuses" in event_details["details"]:
            event_details["details"]["bonuses"] = sorted(list(set(event_details["details"]["bonuses"])))

        return event_details

    def _parse_section(self, section: Tag, event_details: Dict[str, Any]):
        """Parses a single section of the event page."""
        section_id_val = section.get("id")
        if not section_id_val or not isinstance(section_id_val, str):
            return
        section_id = section_id_val

        next_element = section.find_next_sibling()
        while isinstance(next_element, Tag):
            classes = next_element.get("class")
            if (
                next_element.name == "h2"
                and classes
                and "event-section-header" in classes
            ):
                break

            # Handle both pkmn-list and pkmn-list-flex classes
            if next_element.name == "ul" and classes and ("pkmn-list" in classes or "pkmn-list-flex" in classes):
                self._parse_pokemon_list(next_element, section_id, event_details)
            elif next_element.name == "div" and classes and "bonus-list" in classes:
                self._parse_bonuses(next_element, event_details)

            next_element = next_element.find_next_sibling()

        if section_id in event_details["details"]:
            event_details["details"][section_id] = sorted(list(set(event_details["details"][section_id])))

    def _parse_pokemon_list(
        self, element: Tag, section_id: str, event_details: Dict[str, Any]
    ):
        """Parses a list of Pokémon from a section."""
        pokemon_list = set()
        for li in element.find_all("li", class_="pkmn-list-item"):
            pkmn_name_div = li.find("div", class_="pkmn-name")
            if pkmn_name_div:
                pokemon_list.add(clean_spacing(pkmn_name_div.get_text(strip=True)))

        if pokemon_list:
            event_details["details"].setdefault(section_id, []).extend(sorted(list(pokemon_list)))

    def _parse_bonuses(self, element: Tag, event_details: Dict[str, Any]):
        """Parses a list of bonuses."""
        bonuses = {
            clean_spacing(item.get_text(strip=True))
            for item in element.find_all("div", class_="bonus-text")
        }
        if bonuses:
            event_details["details"].setdefault("bonuses", []).extend(sorted(list(bonuses)))

    def scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrapes a given URL for event details with retry logic for invalid times.

        Args:
            url: The URL of the event page to scrape.

        Returns:
            A dictionary containing the scraped event details, or error dict if all retries fail.
        """
        html_path = os.path.join("html", f"event_page_{quote_plus(url)}.html")

        for attempt in range(1, self.max_retries + 1):
            try:
                # Check if cache exists and is valid
                use_cache = self._is_cache_valid(html_path) and attempt == 1

                if use_cache:
                    print(f"Using cached HTML for: {url}")
                    with open(html_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                else:
                    print(f"Scraping dynamic event page: {url} (attempt {attempt}/{self.max_retries})")
                    html_content = self._fetch_dynamic_html(url)

                soup = BeautifulSoup(html_content, "lxml")
                event_details = self._parse_event_details(soup, url)

                # Check if times are valid
                if self._has_valid_times(event_details):
                    # Valid times - save HTML and return
                    if not use_cache:
                        save_html(html_content, html_path)
                    return event_details
                else:
                    # Invalid times
                    print(f"  ⚠️  Invalid start/end time on attempt {attempt}")
                    print(f"     start_time: {event_details.get('start_time')}")
                    print(f"     end_time: {event_details.get('end_time')}")

                    # Delete cache if it exists (it's bad data)
                    if os.path.exists(html_path):
                        os.remove(html_path)
                        print(f"  🗑️  Deleted invalid cache")

                    # If this is not the last attempt, wait and retry
                    if attempt < self.max_retries:
                        print(f"  ⏳ Waiting {self.retry_delay}s before retry...")
                        time.sleep(self.retry_delay)
                    else:
                        print(f"  ❌ All {self.max_retries} attempts failed - skipping event")
                        return {"article_url": url, "error": "InvalidTimes"}

            except TimeoutException as e:
                print(f"Timeout error scraping event page {url} (attempt {attempt}): {e}")
                if attempt == self.max_retries:
                    return {"article_url": url, "error": "TimeoutException"}
                time.sleep(self.retry_delay)

            except AttributeError as e:
                print(f"Attribute error scraping event page {url} (attempt {attempt}): {e}")
                if attempt == self.max_retries:
                    return {"article_url": url, "error": "AttributeError"}
                time.sleep(self.retry_delay)

            except Exception as e:
                print(f"Unexpected error scraping {url} (attempt {attempt}): {e}")
                if attempt == self.max_retries:
                    return {"article_url": url, "error": str(e)}
                time.sleep(self.retry_delay)

        # Should never reach here, but just in case
        return {"article_url": url, "error": "MaxRetriesExceeded"}
