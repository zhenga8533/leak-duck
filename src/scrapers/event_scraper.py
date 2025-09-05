import datetime
import re

from .base_scraper import BaseScraper


class EventScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://leekduck.com/events/", "events")

    def _process_time_data(self, date_string, is_local):
        if not date_string or "calculating" in date_string.lower():
            return None
        try:
            if is_local:
                return date_string[:19]

            dt_object = datetime.datetime.fromisoformat(date_string)
            return int(dt_object.timestamp())
        except (ValueError, TypeError, IndexError):
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
            image_element = link.select_one(".event-img-wrapper img")
            category_element = link.select_one(".event-item-wrapper > p")

            if not title_element:
                continue

            title = title_element.get_text(strip=True)
            article_url = "https://leekduck.com" + link["href"]
            banner_url = image_element["src"].strip() if image_element and "src" in image_element.attrs else None
            category = category_element.get_text(strip=True) if category_element else "Event"

            start_date_str, end_date_str = None, None
            is_local_time = False
            if time_period_element:
                start_date_str = time_period_element.get("data-event-start-date-check") or time_period_element.get(
                    "data-event-start-date"
                )
                end_date_str = time_period_element.get("data-event-end-date")
                is_local_time = time_period_element.get("data-event-local-time") == "true"

            start_time = self._process_time_data(start_date_str, is_local_time)
            end_time = self._process_time_data(end_date_str, is_local_time)

            cleaned_banner_url = self._clean_banner_url(banner_url)

            event_info = {
                "title": title,
                "category": category,
                "is_local_time": is_local_time,
                "start_time": start_time,
                "end_time": end_time,
                "article_url": article_url,
                "banner_url": cleaned_banner_url,
            }
            all_events.append(event_info)

        unique_events = {}
        for event in all_events:
            url = event["article_url"]
            if url not in unique_events:
                unique_events[url] = event
            else:
                existing_event = unique_events[url]
                if event["start_time"] is not None:
                    existing_event["start_time"] = event["start_time"]
                if event["end_time"] is not None:
                    existing_event["end_time"] = event["end_time"]

        events_by_category = {}
        for event in unique_events.values():
            category = event["category"]
            if category not in events_by_category:
                events_by_category[category] = []
            events_by_category[category].append(event)

        return events_by_category
