import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote_plus

from bs4 import BeautifulSoup, Tag

from src.config import ScraperSettings
from src.fetch import get_with_retries
from src.paths import HTML_DIR
from src.utils import clean_banner_url, parse_schedule_datetime, save_html


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


def _classes(tag: Tag) -> list[str]:
    return cast(list[str], tag.get("class") or [])


def _is_section_header(tag: Tag) -> bool:
    return tag.name == "h2" and "event-section-header" in _classes(tag)


def _block_texts(block: Tag, bullet: str = "") -> list[str]:
    """Returns the cleaned text of a paragraph, or of each item in a list."""
    if block.name == "p":
        items = [block]
    elif block.name == "ul":
        items = block.find_all("li", recursive=False)
    else:
        return []

    texts = (clean_spacing(item.get_text(separator=" ", strip=True)) for item in items)
    return [f"{bullet}{text}" if block.name == "ul" else text for text in texts if text]


class EventPageScraper:
    """
    A class to scrape event pages using requests and BeautifulSoup.

    Event pages are server-rendered: dates, descriptions, Pokémon lists, and
    bonuses are all present in the initial HTML response, so no JS execution
    is required to read them.
    """

    def __init__(self, settings: ScraperSettings):
        self.settings = settings

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Checks if the cached HTML file exists and is not expired."""
        if not cache_path.exists():
            return False

        file_modified_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiration_time = datetime.now() - timedelta(
            hours=self.settings.cache_expiration_hours
        )

        return file_modified_time > expiration_time

    def _parse_schedule(self, soup: BeautifulSoup) -> dict[str, Any]:
        """
        Reads the event window from the page's schedule rows.

        Pages list either separate "start" and "end" rows (each timestamp in
        data-start), or one or more "single"/"day" rows spanning
        data-start to data-end.
        """
        schedule = soup.select_one("section.event-schedule")
        is_local = schedule is None or schedule.get("data-local-time") != "false"

        rows = soup.select(".schedule-row[data-start]")
        if not rows:
            return {
                "is_local_time": is_local,
                "start_time": None,
                "end_time": None,
                "schedule_tba": schedule is not None
                and schedule.get("data-mode") == "tba",
            }

        first_row, last_row = rows[0], rows[-1]

        end_value = last_row.get("data-end")
        if end_value is None and last_row.get("data-kind") == "end":
            end_value = last_row.get("data-start")

        return {
            "is_local_time": is_local,
            "start_time": parse_schedule_datetime(
                str(first_row["data-start"]), is_local
            ),
            "end_time": parse_schedule_datetime(
                str(end_value) if end_value else None, is_local
            ),
        }

    def parse(self, soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Parses an event page into its event details."""
        event_details: dict[str, Any] = {"article_url": url, "details": {}}
        content = soup.find("div", class_="page-content")

        if not isinstance(content, Tag):
            return event_details

        event_details.update(self._parse_schedule(soup))

        # Description and embedded sections
        description_div = content.find("div", class_="event-description")
        if isinstance(description_div, Tag):
            description_parts = []
            current_section_id: str | None = None
            current_section_items = []

            for child in description_div.children:
                if not isinstance(child, Tag):
                    continue

                section_id_val = child.get("id")
                if (
                    _is_section_header(child)
                    and section_id_val
                    and isinstance(section_id_val, str)
                ):
                    if current_section_id and current_section_items:
                        event_details["details"][current_section_id] = (
                            current_section_items
                        )
                        current_section_items = []
                    current_section_id = section_id_val
                elif current_section_id:
                    current_section_items.extend(_block_texts(child))
                else:
                    description_parts.extend(_block_texts(child, bullet="- "))

            # Save any remaining section
            if current_section_id and current_section_items:
                event_details["details"][current_section_id] = current_section_items

            if description_parts:
                event_details["description"] = "\n".join(description_parts)

        if not event_details.get("description"):
            unwrapped = self._parse_unwrapped_description(content)
            if unwrapped:
                event_details["description"] = unwrapped

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

    def _parse_unwrapped_description(self, content: Tag) -> str | None:
        """Reads intro prose that is not wrapped in a div.event-description.

        Some pages (Twitch Drops, for example) place their description directly
        in the page content, between the page header and the first section.
        """
        description_parts: list[str] = []
        after_header = False

        for child in content.children:
            if not isinstance(child, Tag):
                continue

            classes = _classes(child)
            if child.name == "div" and "header-page" in classes:
                after_header = True
                continue
            if not after_header:
                continue

            # The description ends where the page's structured content begins.
            if child.name in ("h2", "hr", "style", "script") or (
                child.name == "div" and "event-toc" in classes
            ):
                break

            description_parts.extend(_block_texts(child, bullet="- "))

        return "\n".join(description_parts) or None

    def _parse_section(self, section: Tag, event_details: dict[str, Any]):
        """Parses a single section of the event page."""
        section_id_val = section.get("id")
        if not section_id_val or not isinstance(section_id_val, str):
            return
        section_id = section_id_val

        next_element = section.find_next_sibling()
        while isinstance(next_element, Tag):
            if _is_section_header(next_element):
                break

            classes = _classes(next_element)
            if next_element.name == "ul" and (
                "pkmn-list" in classes or "pkmn-list-flex" in classes
            ):
                self._parse_pokemon_list(next_element, section_id, event_details)
            elif next_element.name == "div" and "bonus-list" in classes:
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
        Scrapes an event page, reusing recently cached HTML when available.

        Note: start_time/end_time parsed here are a fallback only -- EventScraper
        overlays authoritative dates from leekduck.com's official events feed.
        """
        html_path = HTML_DIR / f"event_page_{quote_plus(url)}.html"

        if self._is_cache_valid(html_path):
            print(f"Using cached HTML for: {url}", flush=True)
            html_content = html_path.read_text(encoding="utf-8")
        else:
            html_content = get_with_retries(url, self.settings).text
            save_html(html_content, html_path)

        return self.parse(BeautifulSoup(html_content, "lxml"), url)
