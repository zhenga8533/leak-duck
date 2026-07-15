from datetime import datetime
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

    if not any(data.values()):
        raise OutputValidationError(
            f"{file_name} contains no records; refusing to publish it"
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
            for required_key in (
                "title",
                "article_url",
                "banner_url",
                "category",
                "description",
            ):
                value = event.get(required_key)
                if not isinstance(value, str) or not value.strip():
                    raise OutputValidationError(
                        f"events.{category} entry has invalid {required_key}"
                    )

            if event["category"] != category:
                raise OutputValidationError(
                    f"events.{category} entry has mismatched category "
                    f"{event['category']!r}"
                )

            if not isinstance(event.get("details"), dict):
                raise OutputValidationError(
                    f"events.{category} entry must contain a details object"
                )

            is_local_time = event.get("is_local_time")
            if not isinstance(is_local_time, bool):
                raise OutputValidationError(
                    f"events.{category} entry must declare is_local_time"
                )

            for time_key in ("start_time", "end_time"):
                time_value = event.get(time_key)
                if is_local_time:
                    try:
                        parsed_time = datetime.fromisoformat(time_value)
                    except (TypeError, ValueError):
                        parsed_time = None
                    valid_time = parsed_time is not None and parsed_time.tzinfo is None
                    time_type = "timezone-naive ISO datetime string"
                else:
                    valid_time = isinstance(time_value, int) and not isinstance(
                        time_value, bool
                    )
                    time_type = "unix time"

                if not valid_time:
                    raise OutputValidationError(
                        f"events.{category} entry has invalid {time_key}; "
                        f"expected {time_type}"
                    )
