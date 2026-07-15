from typing import Any


class OutputValidationError(ValueError):
    """Raised when scraped data is unsafe to publish."""


def validate_scraper_output(file_name: str, data: Any) -> None:
    if not isinstance(data, dict) or not data:
        raise OutputValidationError(
            f"{file_name} must be a non-empty JSON object; refusing to publish it"
        )

    for section, entries in data.items():
        if not isinstance(section, str) or not isinstance(entries, list):
            raise OutputValidationError(
                f"{file_name}.{section!s} must be represented by a list"
            )

    if file_name != "events":
        return

    for category, events in data.items():
        for event in events:
            if not isinstance(event, dict):
                raise OutputValidationError(
                    f"events.{category} contains a non-object entry"
                )
            if event.get("error"):
                raise OutputValidationError(
                    f"event page failed for {event.get('article_url', 'unknown URL')}"
                )
            for required_key in ("title", "article_url", "category"):
                if not event.get(required_key):
                    raise OutputValidationError(
                        f"events.{category} entry is missing {required_key}"
                    )
