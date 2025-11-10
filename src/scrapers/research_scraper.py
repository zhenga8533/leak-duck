import re
from typing import Any, cast

from bs4 import BeautifulSoup, Tag

from src.utils import parse_cp_range

from .base_scraper import BaseScraper


class ResearchScraper(BaseScraper):
    def __init__(self, url: str, file_name: str, scraper_settings: dict[str, Any]):
        super().__init__(url, file_name, scraper_settings)

    def parse(self, soup: BeautifulSoup) -> dict[str, Any]:
        research_data: dict[str, Any] = {}
        task_categories = soup.find_all("div", class_="task-category")

        for category in task_categories:
            category = cast(Tag, category)
            category_title_element = category.find("h2")
            if not category_title_element:
                continue

            category_title = category_title_element.get_text(strip=True)
            research_data[category_title] = []

            task_items = category.find_all("li", class_="task-item")

            for item in task_items:
                item = cast(Tag, item)
                task_text_element = item.find("span", class_="task-text")
                if not task_text_element:
                    continue

                task_description = task_text_element.get_text(strip=True)
                rewards_list: list[dict[str, Any]] = []

                reward_elements = item.select("ul.reward-list > li.reward")

                for reward_element in reward_elements:
                    reward_element = cast(Tag, reward_element)
                    reward_type = reward_element.get("data-reward-type", "unknown")
                    reward_label_element = reward_element.find(
                        "span", class_="reward-label"
                    )
                    image_element = reward_element.find("img", class_="reward-image")

                    if not reward_label_element:
                        continue

                    asset_url = (
                        image_element.get("src")
                        if isinstance(image_element, Tag)
                        else None
                    )
                    label_text = reward_label_element.get_text(strip=True)

                    if reward_type == "encounter":
                        is_shiny = (
                            reward_element.find("img", class_="shiny-icon") is not None
                        )
                        cp_values_element = reward_element.find(
                            "span", class_="cp-values"
                        )

                        cp_text = (
                            cp_values_element.get_text(strip=True)
                            if cp_values_element
                            else ""
                        )
                        cp_range = parse_cp_range(cp_text)

                        rewards_list.append(
                            {
                                "type": "encounter",
                                "name": label_text,
                                "shiny_available": is_shiny,
                                "cp_range": cp_range,
                                "asset_url": asset_url,
                            }
                        )
                    else:
                        quantity_element = reward_element.find("div", class_="quantity")
                        quantity = (
                            quantity_element.get_text(strip=True).replace("×", "")
                            if quantity_element
                            else "1"
                        )

                        rewards_list.append(
                            {
                                "type": reward_type,
                                "name": re.sub(r"\s?×\d+$", "", label_text).strip(),
                                "quantity": int(re.sub(r"\D", "", quantity)),
                                "asset_url": asset_url,
                            }
                        )

                if rewards_list:
                    research_data[category_title].append(
                        {"task": task_description, "rewards": rewards_list}
                    )

        return research_data
