from typing import Any, cast

from bs4 import BeautifulSoup, Tag

from src.utils import parse_pokemon_list

from .base_scraper import BaseScraper


class RocketLineupScraper(BaseScraper):
    def __init__(self, url: str, file_name: str, scraper_settings: dict[str, Any]):
        super().__init__(url, file_name, scraper_settings)

    def parse(self, soup: BeautifulSoup) -> dict[str, Any]:
        lineups: dict[str, Any] = {}
        rocket_profiles = soup.find_all("div", class_="rocket-profile")

        for profile in rocket_profiles:
            profile = cast(Tag, profile)
            name_element = profile.find("div", class_="name")
            if not name_element:
                continue

            leader_name = name_element.get_text(strip=True)
            lineups[leader_name] = []

            slots = profile.select(".lineup-info .slot")
            for i, slot in enumerate(slots, 1):
                slot = cast(Tag, slot)
                pokemon_in_slot = parse_pokemon_list(slot)

                if pokemon_in_slot:
                    classes = slot.get("class")
                    is_encounter_slot = classes is not None and "encounter" in classes
                    lineups[leader_name].append(
                        {
                            "slot": i,
                            "pokemons": pokemon_in_slot,
                            "is_encounter": is_encounter_slot,
                        }
                    )
        return lineups
