import os
from typing import Any, Dict

from bs4 import BeautifulSoup
from bs4.element import NavigableString
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils import process_time_data


class EventPageScraper:
    def __init__(self):
        self.driver = self.get_driver()

    def get_driver(self) -> WebDriver:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        service = Service(log_output=os.devnull)

        return webdriver.Chrome(service=service, options=options)

    def fetch_dynamic_html(self, url: str) -> str:
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

    def close(self) -> None:
        self.driver.quit()

    def scrape(self, url: str) -> Dict[str, Any]:
        try:
            print(f"Scraping dynamic event page: {url}")
            html_content = self.fetch_dynamic_html(url)
            soup = BeautifulSoup(html_content, "lxml")

            event_details: Dict[str, Any] = {"article_url": url}
            content = soup.find("div", class_="page-content")

            if not content or isinstance(content, NavigableString):
                return event_details

            start_date_element = soup.find("span", id="event-date-start")
            start_time_element = soup.find("span", id="event-time-start")
            end_date_element = soup.find("span", id="event-date-end")
            end_time_element = soup.find("span", id="event-time-end")

            is_local = not (start_date_element and "data-event-page-date" in start_date_element.attrs)
            event_details["is_local_time"] = is_local

            event_details["start_time"] = process_time_data(start_date_element, start_time_element, is_local)
            event_details["end_time"] = process_time_data(end_date_element, end_time_element, is_local)

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

        except TimeoutException as e:
            print(f"Timeout error scraping event page {url}: {e}")
            return {"article_url": url, "error": "TimeoutException"}
        except AttributeError as e:
            print(f"Attribute error scraping event page {url}: {e}")
            return {"article_url": url, "error": "AttributeError"}
        except Exception as e:
            print(f"An unexpected error occurred while scraping {url}: {e}")
            return {"article_url": url, "error": str(e)}
