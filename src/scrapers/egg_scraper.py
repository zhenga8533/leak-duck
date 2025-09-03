from .base_scraper import BaseScraper


class EggScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://leekduck.com/eggs/", "egg_pool")

    def parse(self, soup):
        egg_pool = {}
        # Find all <h2> elements which are the titles for the egg groups
        egg_group_titles = soup.select("article.article-page h2")

        for title_element in egg_group_titles:
            # The list of Pokémon is in the <ul> element that comes right after the <h2>
            egg_grid = title_element.find_next_sibling("ul", class_="egg-grid")

            # If there's no grid of eggs following this title, skip to the next one
            if not egg_grid:
                continue

            egg_group_name = title_element.get_text(strip=True)
            egg_pool[egg_group_name] = []

            # Find all list items with the class 'pokemon-card' inside the grid
            pokemon_cards = egg_grid.find_all("li", class_="pokemon-card")

            for card in pokemon_cards:
                name_element = card.find("span", class_="name")
                if not name_element:
                    continue

                name = name_element.get_text(strip=True)
                # Check for the existence of the shiny icon
                is_shiny = card.find("svg", class_="shiny-icon") is not None
                # Count the number of rarity eggs (1-5)
                rarity = len(card.select("div.rarity > svg.mini-egg"))

                pokemon_data = {"name": name, "shiny_available": is_shiny, "rarity_tier": rarity}
                egg_pool[egg_group_name].append(pokemon_data)

        return egg_pool
