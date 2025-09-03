import datetime
import re

from .base_scraper import BaseScraper


class EventScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://leekduck.com/events/", "events")

    def _to_unix_timestamp(self, date_string):
        if not date_string or "calculating" in date_string.lower():
            return None
        try:
            dt_object = datetime.datetime.fromisoformat(date_string)
            return int(dt_object.timestamp())
        except (ValueError, TypeError):
            return None

    def _clean_banner_url(self, url):
        if not url:
            return None
        return re.sub(r"cdn-cgi/image/.*?\/(?=assets)", "", url)

    def parse(self, soup):
        all_events = []
        event_links = soup.select("a.event-item-link")

        for link in event_links:
            wrapper = link.find_parent("span", class_="event-header-item-wrapper")
            time_period_element = wrapper.find("h5", class_="event-header-time-period") if wrapper else None

            title_element = link.select_one("div.event-text h2")
            date_element = link.select_one("div.event-text p")
            image_element = link.select_one(".event-img-wrapper img")
            category_element = link.select_one(".event-item-wrapper > p")

            if not title_element or not date_element:
                continue

            title = title_element.get_text(strip=True)
            time_string = date_element.get_text(strip=True)
            article_url = "https://leekduck.com" + link["href"]
            banner_url = image_element["src"].strip() if image_element and "src" in image_element.attrs else None
            category = category_element.get_text(strip=True) if category_element else "Event"

            start_date_str = time_period_element.get("data-event-start-date-check") if time_period_element else None
            end_date_str = time_period_element.get("data-event-end-date") if time_period_element else None

            start_timestamp = self._to_unix_timestamp(start_date_str)
            end_timestamp = self._to_unix_timestamp(end_date_str)

            cleaned_banner_url = self._clean_banner_url(banner_url)

            event_info = {
                "title": title,
                "category": category,
                "time_string": time_string,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "article_url": article_url,
                "banner_url": cleaned_banner_url,
            }
            all_events.append(event_info)

        unique_events = []
        seen_urls = set()
        for event in all_events:
            if event["article_url"] not in seen_urls:
                unique_events.append(event)
                seen_urls.add(event["article_url"])

        events_by_category = {}
        for event in unique_events:
            category = event["category"]
            if category not in events_by_category:
                events_by_category[category] = []
            events_by_category[category].append(event)

        return events_by_category
