import datetime
import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class EventPageScraper:
    def __init__(self):
        self.driver = self.get_driver()

    def get_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        service = Service()
        return webdriver.Chrome(service=service, options=options)

    def fetch_dynamic_html(self, url):
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#event-time-date-box span[data-event-page-date], #event-time-date-box span:not([data-event-page-date])",
                )
            )
        )
        return self.driver.page_source

    def close(self):
        self.driver.quit()

    def scrape(self, url):
        try:
            print(f"Scraping dynamic event page: {url}")
            html_content = self.fetch_dynamic_html(url)
            soup = BeautifulSoup(html_content, "lxml")

            event_details = {"article_url": url}
            content = soup.find("div", class_="page-content")

            if not content or isinstance(content, NavigableString):
                return event_details

            start_date_element = soup.find("span", id="event-date-start")
            start_time_element = soup.find("span", id="event-time-start")
            end_date_element = soup.find("span", id="event-date-end")
            end_time_element = soup.find("span", id="event-time-end")

            is_local = not (start_date_element and "data-event-page-date" in start_date_element.attrs)
            event_details["is_local_time"] = is_local

            event_details["start_time"] = self.process_time_data(start_date_element, start_time_element, is_local)
            event_details["end_time"] = self.process_time_data(end_date_element, end_time_element, is_local)

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

        except Exception as e:
            print(f"Error scraping event page {url}: {e}")
            return {"article_url": url}

    def process_time_data(self, date_element, time_element, is_local):
        if is_local:
            if date_element and time_element:
                raw_date_str = date_element.get_text(strip=True)
                raw_time_str = time_element.get_text(strip=True)
                date_str = re.sub(r"\s+", " ", raw_date_str).replace(",", "").strip()
                time_str = re.sub(r"\s+", " ", raw_time_str).replace("at", "").replace("Local Time", "").strip()
                datetime_str = f"{date_str} {time_str}"
                try:
                    dt_object = datetime.datetime.strptime(datetime_str, "%A %B %d %Y %I:%M %p")
                    return dt_object.isoformat()
                except ValueError:
                    return None
        else:
            if date_element and "data-event-page-date" in date_element.attrs:
                iso_string = date_element["data-event-page-date"]
                try:
                    dt_object = datetime.datetime.fromisoformat(iso_string)
                    return int(dt_object.timestamp())
                except (ValueError, TypeError):
                    return None
        return None
