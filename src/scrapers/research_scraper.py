import re
from typing import Any, cast

from bs4 import BeautifulSoup, Tag

from src.utils import parse_cp_range

from .base_scraper import BaseScraper


class ResearchScraper(BaseScraper):
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
                rewards_list = [
                    reward
                    for reward_element in item.select("ul.reward-list > li.reward")
                    if (reward := self._parse_reward(cast(Tag, reward_element)))
                ]

                if rewards_list:
                    research_data[category_title].append(
                        {"task": task_description, "rewards": rewards_list}
                    )

        return research_data

    def _parse_reward(self, reward_element: Tag) -> dict[str, Any] | None:
        reward_label_element = reward_element.find("span", class_="reward-label")
        if not reward_label_element:
            return None

        reward_type = reward_element.get("data-reward-type", "unknown")
        image_element = reward_element.find("img", class_="reward-image")
        asset_url = image_element.get("src") if isinstance(image_element, Tag) else None
        label_text = reward_label_element.get_text(strip=True)

        if reward_type == "encounter":
            cp_values_element = reward_element.find("span", class_="cp-values")
            cp_text = (
                cp_values_element.get_text(strip=True) if cp_values_element else ""
            )
            return {
                "type": "encounter",
                "name": label_text,
                "shiny_available": reward_element.find("img", class_="shiny-icon")
                is not None,
                "cp_range": parse_cp_range(cp_text),
                "asset_url": asset_url,
            }

        quantity_element = reward_element.find("div", class_="quantity")
        quantity_text = (
            quantity_element.get_text(strip=True) if quantity_element else ""
        )
        return {
            "type": reward_type,
            "name": re.sub(r"\s?×\d+$", "", label_text).strip(),
            "quantity": self._parse_quantity(quantity_text, label_text),
            "asset_url": asset_url,
        }

    @staticmethod
    def _parse_quantity(quantity_text: str, label_text: str) -> int:
        # The quantity div is sometimes present but empty or non-numeric, so
        # fall back to a "×N" suffix on the label, then to a single reward.
        digits = re.sub(r"\D", "", quantity_text)
        if digits:
            return int(digits)
        label_match = re.search(r"×\s?([\d,.]+)$", label_text)
        if label_match and (label_digits := re.sub(r"\D", "", label_match.group(1))):
            return int(label_digits)
        return 1
