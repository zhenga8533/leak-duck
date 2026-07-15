import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup, Tag

from src.paths import HTML_DIR
from src.utils import clean_banner_url, process_time_data, save_html


def clean_spacing(text: str) -> str:
    """
    Cleans up extra spaces around punctuation marks.

    Args:
        text: The text to clean.

    Returns:
        The cleaned text with proper spacing around punctuation.
    """
    # Remove spaces before punctuation marks
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    # Remove spaces after opening parentheses/brackets
    text = re.sub(r"([\(\[])\s+", r"\1", text)
    # Remove spaces before closing parentheses/brackets
    text = re.sub(r"\s+([\)\]])", r"\1", text)
    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class EventPageScraper:
    """
    A class to scrape event pages using requests and BeautifulSoup.

    Event pages are server-rendered: dates, descriptions, Pokémon lists, and
    bonuses are all present in the initial HTML response, so no JS execution
    is required to read them.
    """

    def __init__(self, scraper_settings: dict[str, Any] | None = None):
        settings = scraper_settings or {}
        self.cache_expiration_hours = settings.get("cache_expiration_hours", 1)
        self.max_retries = settings.get("retries", 3)
        self.retry_delay = settings.get("delay", 1)
        self.timeout = settings.get("timeout", 15)

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Checks if the cached HTML file exists and is not expired."""
        if not cache_path.exists():
            return False

        file_modified_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiration_time = datetime.now() - timedelta(hours=self.cache_expiration_hours)

        return file_modified_time > expiration_time

    def _fetch_html(self, url: str) -> str:
        """Fetches the HTML content of an event page."""
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _parse_event_details(self, soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Parses the HTML soup to extract event details."""
        event_details: dict[str, Any] = {"article_url": url, "details": {}}
        content = soup.find("div", class_="page-content")

        if not isinstance(content, Tag):
            return event_details

        # Time details
        start_date_element = cast(Tag | None, soup.find("span", id="event-date-start"))
        start_time_element = cast(Tag | None, soup.find("span", id="event-time-start"))
        end_date_element = cast(Tag | None, soup.find("span", id="event-date-end"))
        end_time_element = cast(Tag | None, soup.find("span", id="event-time-end"))

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
            current_section_id: str | None = None
            current_section_items = []

            for child in description_div.children:
                if not isinstance(child, Tag):
                    continue

                # Check if this is a section header (h2 with id and event-section-header class)
                section_id_val = child.get("id")
                classes = cast(list, child.get("class") or [])
                if (
                    child.name == "h2"
                    and section_id_val
                    and isinstance(section_id_val, str)
                    and "event-section-header" in classes
                ):
                    # Save current section if we were in one
                    if current_section_id and current_section_items:
                        event_details["details"][current_section_id] = (
                            current_section_items
                        )
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
            self._parse_section(cast(Tag, section), event_details)

        # Final cleanup - move bonuses to details if it exists
        if "bonuses" in event_details["details"]:
            event_details["details"]["bonuses"] = sorted(
                list(set(event_details["details"]["bonuses"]))
            )

        return event_details

    def _parse_section(self, section: Tag, event_details: dict[str, Any]):
        """Parses a single section of the event page."""
        section_id_val = section.get("id")
        if not section_id_val or not isinstance(section_id_val, str):
            return
        section_id = section_id_val

        next_element = section.find_next_sibling()
        while isinstance(next_element, Tag):
            classes = cast(list, next_element.get("class") or [])
            if (
                next_element.name == "h2"
                and classes
                and "event-section-header" in classes
            ):
                break

            # Handle both pkmn-list and pkmn-list-flex classes
            if (
                next_element.name == "ul"
                and classes
                and ("pkmn-list" in classes or "pkmn-list-flex" in classes)
            ):
                self._parse_pokemon_list(next_element, section_id, event_details)
            elif next_element.name == "div" and classes and "bonus-list" in classes:
                self._parse_bonuses(next_element, event_details)

            next_element = next_element.find_next_sibling()

        if section_id in event_details["details"]:
            items = event_details["details"][section_id]
            if items and isinstance(items[0], dict):
                # Pokémon entries: dedupe by name (dicts aren't hashable for set()).
                deduped_by_name = {item["name"]: item for item in items}
                event_details["details"][section_id] = sorted(
                    deduped_by_name.values(), key=lambda p: p["name"]
                )
            else:
                event_details["details"][section_id] = sorted(list(set(items)))

    def _parse_pokemon_list(
        self, element: Tag, section_id: str, event_details: dict[str, Any]
    ):
        """Parses a list of Pokémon from a section, including asset URL and shiny availability."""
        pokemon_list = []
        seen_names = set()
        for li in element.find_all("li", class_="pkmn-list-item"):
            li_tag = cast(Tag, li)
            pkmn_name_div = cast(Tag | None, li_tag.find("div", class_="pkmn-name"))
            if not pkmn_name_div:
                continue

            name = clean_spacing(pkmn_name_div.get_text(strip=True))
            if name in seen_names:
                continue
            seen_names.add(name)

            asset_img = cast(Tag | None, li_tag.select_one(".pkmn-list-img img"))
            asset_url = (
                clean_banner_url(asset_img["src"])
                if asset_img and asset_img.has_attr("src")
                else None
            )
            is_shiny = li_tag.find("img", class_="shiny-icon") is not None

            pokemon_list.append(
                {"name": name, "asset_url": asset_url, "shiny_available": is_shiny}
            )

        if pokemon_list:
            event_details["details"].setdefault(section_id, []).extend(pokemon_list)

    def _parse_bonuses(self, element: Tag, event_details: dict[str, Any]):
        """Parses a list of bonuses."""
        bonuses = {
            clean_spacing(item.get_text(strip=True))
            for item in element.find_all("div", class_="bonus-text")
        }
        if bonuses:
            event_details["details"].setdefault("bonuses", []).extend(
                sorted(list(bonuses))
            )

    def scrape(self, url: str) -> dict[str, Any]:
        """
        Scrapes a given URL for event details, retrying on request errors.

        Note: start_time/end_time parsed here are a fallback only -- EventScraper
        overlays authoritative dates from leekduck.com's official events feed.

        Args:
            url: The URL of the event page to scrape.

        Returns:
            A dictionary containing the scraped event details.

        Raises:
            RuntimeError: If fetching or parsing fails after all retries.
        """
        html_path = HTML_DIR / f"event_page_{quote_plus(url)}.html"

        for attempt in range(1, self.max_retries + 1):
            try:
                use_cache = self._is_cache_valid(html_path) and attempt == 1

                if use_cache:
                    print(f"Using cached HTML for: {url}", flush=True)
                    with html_path.open("r", encoding="utf-8") as f:
                        html_content = f.read()
                else:
                    print(
                        f"Scraping event page: {url} (attempt {attempt}/{self.max_retries})",
                        flush=True,
                    )
                    html_content = self._fetch_html(url)

                soup = BeautifulSoup(html_content, "lxml")
                event_details = self._parse_event_details(soup, url)

                if not use_cache:
                    save_html(html_content, html_path)
                return event_details

            except requests.exceptions.RequestException as e:
                print(
                    f"Request error scraping event page {url} (attempt {attempt}): {e}",
                    flush=True,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise RuntimeError(
                        f"Failed to scrape event page {url} after {self.max_retries} attempts"
                    ) from e

            except Exception as e:
                print(
                    f"Unexpected error scraping {url} (attempt {attempt}): {e}",
                    flush=True,
                )
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed to parse event page {url} after {self.max_retries} attempts"
                    ) from e
                time.sleep(self.retry_delay)

        # Should never reach here, but just in case
        raise RuntimeError(f"Failed to scrape event page {url}")
