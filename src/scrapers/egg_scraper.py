from .base_scraper import BaseScraper


class EggScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://leekduck.com/eggs/", "egg_pool")

    def parse(self, soup):
        egg_pool = {}
        egg_group_titles = soup.select("article.article-page h2")

        for title_element in egg_group_titles:
            egg_grid = title_element.find_next_sibling("ul", class_="egg-grid")

            if not egg_grid:
                continue

            egg_group_name = title_element.get_text(strip=True)
            egg_pool[egg_group_name] = []

            pokemon_cards = egg_grid.find_all("li", class_="pokemon-card")

            for card in pokemon_cards:
                name_element = card.find("span", class_="name")
                if not name_element:
                    continue

                name = name_element.get_text(strip=True)
                is_shiny = card.find("svg", class_="shiny-icon") is not None
                rarity = len(card.select("div.rarity > svg.mini-egg"))
                asset_url = card.select_one("div.icon img")["src"]

                pokemon_data = {
                    "name": name,
                    "shiny_available": is_shiny,
                    "rarity_tier": rarity,
                    "asset_url": asset_url,
                }
                egg_pool[egg_group_name].append(pokemon_data)

        return egg_pool
