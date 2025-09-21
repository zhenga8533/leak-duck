import re
from typing import Any, Dict

from bs4 import BeautifulSoup

from src.utils import parse_cp_range

from .base_scraper import BaseScraper


class RaidBossScraper(BaseScraper):
    def __init__(self, url: str, file_name: str, scraper_settings: Dict[str, Any]):
        super().__init__(url, file_name, scraper_settings)

    def parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        raid_data: Dict[str, Any] = {}
        tier_sections = soup.select(".raid-bosses .tier, .shadow-raid-bosses .tier")

        for section in tier_sections:
            header_element = section.find("h2", class_="header")
            if not header_element:
                continue

            tier_name = header_element.get_text(strip=True)
            raid_data[tier_name] = []

            boss_cards = section.find_all("div", class_="card")

            for card in boss_cards:
                name_element = card.find("p", class_="name")
                if not name_element:
                    continue

                name = name_element.get_text(strip=True)
                is_shiny = card.find("svg", class_="shiny-icon") is not None

                tier_match = re.search(r"\d+", tier_name)
                tier_value = int(tier_match.group(0)) if tier_match else tier_name

                cp_range_element = card.find("div", class_="cp-range")
                cp_range_str = cp_range_element.get_text(strip=True) if cp_range_element else ""

                boosted_cp_element = card.find("div", class_="boosted-cp-row")
                boosted_cp_str = boosted_cp_element.get_text(strip=True) if boosted_cp_element else ""

                types = [t["title"] for t in card.select(".boss-type .type img")]

                asset_url = card.select_one(".boss-img img")["src"]

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
