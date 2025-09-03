import re

from .base_scraper import BaseScraper


class RaidBossScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://leekduck.com/boss/", "raid_bosses")

    def _parse_cp_range(self, cp_string):
        if not cp_string or "-" not in cp_string:
            return None

        numbers = re.findall(r"\d+", cp_string)
        if len(numbers) == 2:
            return {"min": int(numbers[0]), "max": int(numbers[1])}
        return None

    def parse(self, soup):
        raid_data = {}
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

                boss_info = {
                    "name": name,
                    "tier": tier_value,
                    "shiny_available": is_shiny,
                    "cp_range": self._parse_cp_range(cp_range_str),
                    "boosted_cp_range": self._parse_cp_range(boosted_cp_str),
                    "types": types,
                }
                raid_data[tier_name].append(boss_info)

        return raid_data
