import os
from typing import Any, Dict
from urllib.parse import quote_plus

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils import process_time_data, save_html


class EventPageScraper:
    """
    A class to scrape dynamic event pages using Selenium and BeautifulSoup.

    This scraper is designed to fetch and parse event details from pages that
    load their content dynamically using JavaScript.
    """

    def __init__(self):
        """Initializes the EventPageScraper and its WebDriver."""
        self.driver: WebDriver = self._get_driver()

    def _get_driver(self) -> WebDriver:
        """Configures and returns a headless Chrome WebDriver instance."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # This will make the driver wait for the initial HTML to load, but not for all
        # resources like images and stylesheets. This can prevent the scraper from
        # getting stuck on pages with slow-loading assets.
        options.page_load_strategy = "eager"

        service = Service(log_output=os.devnull)
        return webdriver.Chrome(service=service, options=options)

    def _fetch_dynamic_html(self, url: str) -> str:
        """Fetches the HTML content of a page after dynamic content has loaded."""
        # This will raise a TimeoutException if the page takes more than 30 seconds to load
        self.driver.set_page_load_timeout(30)
        self.driver.get(url)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#event-time-date-box span[data-event-page-date], "
                    "#event-time-date-box span:not([data-event-page-date])",
                )
            )
        )
        return self.driver.page_source

    def close(self) -> None:
        """Closes the WebDriver session."""
        self.driver.quit()

    def _parse_event_details(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parses the HTML soup to extract event details."""
        event_details: Dict[str, Any] = {"article_url": url}
        content = soup.find("div", class_="page-content")

        if not isinstance(content, Tag):
            return event_details

        # Time details
        start_date_element = soup.find("span", id="event-date-start")
        start_time_element = soup.find("span", id="event-time-start")
        end_date_element = soup.find("span", id="event-date-end")
        end_time_element = soup.find("span", id="event-time-end")

        is_local = not (
            isinstance(start_date_element, Tag)
            and "data-event-page-date" in start_date_element.attrs
        )
        event_details["is_local_time"] = is_local

        event_details["start_time"] = process_time_data(
            start_date_element, start_time_element, is_local
        )
        event_details["end_time"] = process_time_data(
            end_date_element, end_time_element, is_local
        )

        # Description
        description_div = content.find("div", class_="event-description")
        if isinstance(description_div, Tag):
            description_texts = [
                p.get_text(separator=" ", strip=True)
                for p in description_div.find_all("p", recursive=False)
            ]
            event_details["description"] = "\n".join(description_texts)

        # Main sections
        main_sections = content.find_all("h2", class_="event-section-header")
        for section in main_sections:
            self._parse_section(section, event_details)

        # Final cleanup
        if "bonuses" in event_details:
            event_details["bonuses"] = sorted(list(set(event_details["bonuses"])))

        return event_details

    def _parse_section(self, section: Tag, event_details: Dict[str, Any]):
        """Parses a single section of the event page."""
        section_id_val = section.get("id")
        if not section_id_val or not isinstance(section_id_val, str):
            return
        section_id = section_id_val

        next_element = section.find_next_sibling()
        while isinstance(next_element, Tag):
            classes = next_element.get("class")
            if (
                next_element.name == "h2"
                and classes
                and "event-section-header" in classes
            ):
                break

            if next_element.name == "ul" and classes and "pkmn-list" in classes:
                self._parse_pokemon_list(next_element, section_id, event_details)
            elif next_element.name == "div" and classes and "bonus-list" in classes:
                self._parse_bonuses(next_element, event_details)

            next_element = next_element.find_next_sibling()

        if section_id in event_details:
            event_details[section_id] = sorted(list(set(event_details[section_id])))

    def _parse_pokemon_list(
        self, element: Tag, section_id: str, event_details: Dict[str, Any]
    ):
        """Parses a list of Pokémon from a section."""
        pokemon_list = set()
        for li in element.find_all("li", class_="pkmn-list-item"):
            pkmn_name_div = li.find("div", class_="pkmn-name")
            if pkmn_name_div:
                pokemon_list.add(pkmn_name_div.get_text(strip=True))

        if pokemon_list:
            event_details.setdefault(section_id, []).extend(sorted(list(pokemon_list)))

    def _parse_bonuses(self, element: Tag, event_details: Dict[str, Any]):
        """Parses a list of bonuses."""
        bonuses = {
            item.get_text(strip=True)
            for item in element.find_all("div", class_="bonus-text")
        }
        if bonuses:
            event_details.setdefault("bonuses", []).extend(sorted(list(bonuses)))

    def scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrapes a given URL for event details.

        Args:
            url: The URL of the event page to scrape.

        Returns:
            A dictionary containing the scraped event details.
        """
        try:
            print(f"Scraping dynamic event page: {url}")
            html_content = self._fetch_dynamic_html(url)
            html_path = os.path.join("html", f"event_page_{quote_plus(url)}.html")
            save_html(html_content, html_path)

            soup = BeautifulSoup(html_content, "lxml")
            return self._parse_event_details(soup, url)

        except TimeoutException as e:
            print(f"Timeout error scraping event page {url}: {e}")
            return {"article_url": url, "error": "TimeoutException"}
        except AttributeError as e:
            print(f"Attribute error scraping event page {url}: {e}")
            return {"article_url": url, "error": "AttributeError"}
        except Exception as e:
            print(f"An unexpected error occurred while scraping {url}: {e}")
            return {"article_url": url, "error": str(e)}
