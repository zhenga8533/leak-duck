from .base_scraper import BaseScraper


class RocketLineupScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://leekduck.com/rocket-lineups/", "rocket_lineups")

    def parse(self, soup):
        lineups = {}
        rocket_profiles = soup.find_all("div", class_="rocket-profile")

        for profile in rocket_profiles:
            name_element = profile.find("div", class_="name")
            if not name_element:
                continue

            leader_name = name_element.get_text(strip=True)
            lineups[leader_name] = []

            slots = profile.select(".lineup-info .slot")

            for i, slot in enumerate(slots, 1):
                pokemon_in_slot = []
                pokemon_elements = slot.find_all("span", class_="shadow-pokemon")

                for p in pokemon_elements:
                    pokemon_name = p["data-pokemon"]
                    is_shiny = p.find("svg", class_="shiny-icon") is not None
                    asset_url = p.select_one("img.pokemon-image")["src"]

                    pokemon_in_slot.append({"name": pokemon_name, "shiny_available": is_shiny, "asset_url": asset_url})

                if pokemon_in_slot:
                    is_encounter_slot = "encounter" in slot.get("class", [])

                    lineups[leader_name].append(
                        {"slot": i, "pokemons": pokemon_in_slot, "is_encounter": is_encounter_slot}
                    )

        return lineups
