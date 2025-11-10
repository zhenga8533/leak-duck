import re
from typing import Any, cast

from bs4 import BeautifulSoup, Tag

from src.utils import parse_cp_range

from .base_scraper import BaseScraper


class RaidBossScraper(BaseScraper):
    def __init__(self, url: str, file_name: str, scraper_settings: dict[str, Any]):
        super().__init__(url, file_name, scraper_settings)

    def parse(self, soup: BeautifulSoup) -> dict[str, Any]:
        raid_data: dict[str, Any] = {}
        tier_sections = soup.select(".raid-bosses .tier, .shadow-raid-bosses .tier")

        for section in tier_sections:
            section = cast(Tag, section)
            header_element = section.find("h2", class_="header")
            if not header_element:
                continue

            tier_name = header_element.get_text(strip=True)
            raid_data[tier_name] = []

            boss_cards = section.find_all("div", class_="card")

            for card in boss_cards:
                card = cast(Tag, card)
                name_element = card.find("p", class_="name")
                if not name_element:
                    continue

                name = name_element.get_text(strip=True)
                is_shiny = card.find("svg", class_="shiny-icon") is not None

                tier_match = re.search(r"\d+", tier_name)
                tier_value: Any = int(tier_match.group(0)) if tier_match else tier_name

                cp_range_element = card.find("div", class_="cp-range")
                cp_range_str = (
                    cp_range_element.get_text(strip=True) if cp_range_element else ""
                )

                boosted_cp_element = card.find("div", class_="boosted-cp-row")
                boosted_cp_str = (
                    boosted_cp_element.get_text(strip=True)
                    if boosted_cp_element
                    else ""
                )

                types = [
                    cast(Tag, t)["title"]
                    for t in card.select(".boss-type .type img")
                    if cast(Tag, t).has_attr("title")
                ]

                asset_url_element = card.select_one(".boss-img img")
                asset_url = (
                    asset_url_element["src"]
                    if asset_url_element and asset_url_element.has_attr("src")
                    else None
                )

                boss_info = {
                    "name": name,
                    "tier": tier_value,
                    "shiny_available": is_shiny,
                    "cp_range": parse_cp_range(cp_range_str),
                    "boosted_cp_range": parse_cp_range(boosted_cp_str),
                    "types": types,
                    "asset_url": asset_url,
                }
                raid_data[tier_name].append(boss_info)

        return raid_data
