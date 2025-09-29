import re
from typing import Any, Dict

from bs4 import BeautifulSoup, Tag

from src.utils import parse_pokemon_list

from .base_scraper import BaseScraper


class EggScraper(BaseScraper):
    def __init__(self, url: str, file_name: str, scraper_settings: Dict[str, Any]):
        super().__init__(url, file_name, scraper_settings)

    def parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        egg_pool: Dict[str, Any] = {}
        egg_group_titles = soup.select("article.article-page h2")

        for title_element in egg_group_titles:
            egg_grid = title_element.find_next_sibling("ul", class_="egg-grid")
            if not isinstance(egg_grid, Tag):
                continue

            egg_group_name = title_element.get_text(strip=True)
            distance_match = re.search(r"\d+", egg_group_name)
            hatch_distance = int(distance_match.group(0)) if distance_match else None

            pokemon_data = parse_pokemon_list(egg_grid)

            for pokemon in pokemon_data:
                pokemon["hatch_distance"] = hatch_distance
                name_span = egg_grid.find("span", class_="name", string=pokemon["name"])
                if name_span:
                    card = name_span.find_parent("li")
                    if card:
                        pokemon["rarity_tier"] = len(
                            card.select("div.rarity > svg.mini-egg")
                        )

            egg_pool[egg_group_name] = pokemon_data

        return egg_pool
