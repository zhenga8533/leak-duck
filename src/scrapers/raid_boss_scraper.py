import re
from typing import Any, cast

from bs4 import BeautifulSoup, Tag

from src.utils import parse_cp_range, parse_pokemon_list

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
            tier_match = re.search(r"\d+", tier_name)
            tier_value: Any = int(tier_match.group(0)) if tier_match else tier_name

            # name/shiny_available/asset_url come from the shared helper; tier/CP/type
            # info is raid-specific and merged in by matching on name below.
            pokemon_by_name = {p["name"]: p for p in parse_pokemon_list(section)}

            for card in section.find_all("div", class_="card"):
                card = cast(Tag, card)
                name_element = card.find("p", class_="name")
                if not name_element:
                    continue

                boss_info = pokemon_by_name.get(name_element.get_text(strip=True))
                if boss_info is None:
                    continue

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

                boss_info.update(
                    {
                        "tier": tier_value,
                        "cp_range": parse_cp_range(cp_range_str),
                        "boosted_cp_range": parse_cp_range(boosted_cp_str),
                        "types": types,
                    }
                )

            raid_data[tier_name] = list(pokemon_by_name.values())

        return raid_data
