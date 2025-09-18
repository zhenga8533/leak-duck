import requests
from bs4 import BeautifulSoup, NavigableString


class EventPageScraper:
    def scrape(self, url):
        try:
            print(f"Scraping event page: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "lxml")

            event_details = {"article_url": url}
            content = soup.find("div", class_="page-content")

            if not content or isinstance(content, NavigableString):
                return event_details

            description_div = content.find("div", class_="event-description")
            if description_div and not isinstance(description_div, NavigableString):
                description_texts = [p.get_text(strip=True) for p in description_div.find_all("p", recursive=False)]
                event_details["description"] = "\n".join(description_texts)

            main_sections = content.find_all("h2", class_="event-section-header")
            for section in main_sections:
                section_id = section.get("id")
                if not section_id:
                    continue

                next_element = section.find_next_sibling()
                while next_element:
                    if isinstance(next_element, NavigableString):
                        next_element = next_element.find_next_sibling()
                        continue

                    if next_element.name == "h2" and "event-section-header" in next_element.get("class", []):
                        break

                    if next_element.name == "ul" and "pkmn-list-flex" in next_element.get("class", []):
                        pokemon_list = {
                            li.find("div", class_="pkmn-name").get_text(strip=True)
                            for li in next_element.find_all("li", class_="pkmn-list-item")
                            if li.find("div", class_="pkmn-name")
                        }
                        if pokemon_list:
                            event_details.setdefault(section_id, []).extend(sorted(list(pokemon_list)))

                    if next_element.name == "div" and "bonus-list" in next_element.get("class", []):
                        bonuses = {
                            item.get_text(strip=True) for item in next_element.find_all("div", class_="bonus-text")
                        }
                        if bonuses:
                            event_details.setdefault("bonuses", []).extend(sorted(list(bonuses)))

                    next_element = next_element.find_next_sibling()

                if section_id in event_details:
                    event_details[section_id] = sorted(list(set(event_details[section_id])))

            if "bonuses" in event_details:
                event_details["bonuses"] = sorted(list(set(event_details["bonuses"])))

            return event_details

        except requests.exceptions.RequestException as e:
            print(f"Error fetching event page {url}: {e}")
            return {"article_url": url}
