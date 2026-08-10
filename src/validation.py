from datetime import datetime
from typing import Any


class OutputValidationError(ValueError):
    """Raised when scraped data is unsafe to publish."""


def validate_scraper_output(file_name: str, data: Any) -> None:
    """Validate freshly scraped output before it is published.

    Event records must be complete, including a non-empty ``description``.
    """
    _validate_sections(file_name, data, allow_empty=False)

    if file_name != "events":
        return

    _validate_event_records(file_name, data, require_description=True)


def validate_archive_output(
    file_name: str, data: Any, allow_empty: bool = False
) -> None:
    """Validate a historical event archive.

    Archives are point-in-time snapshots, so legacy records archived before the
    field was captured may omit ``description``; when present it must be a
    string. Pokémon detail entries may use the legacy plain-string format or the
    current Pokémon object format. Every other field is validated as strictly as
    freshly scraped events.
    """
    _validate_sections(file_name, data, allow_empty=allow_empty)

    if allow_empty and not data:
        return

    _validate_event_records(file_name, data, require_description=False)


def _validate_sections(file_name: str, data: Any, allow_empty: bool) -> None:
    if not isinstance(data, dict) or (not data and not allow_empty):
        raise OutputValidationError(
            f"{file_name} must be a non-empty JSON object; refusing to publish it"
        )

    for section, entries in data.items():
        if not isinstance(section, str) or not isinstance(entries, list):
            raise OutputValidationError(
                f"{file_name}.{section!s} must be represented by a list"
            )

    if not any(data.values()) and not allow_empty:
        raise OutputValidationError(
            f"{file_name} contains no records; refusing to publish it"
        )


def _validate_event_records(
    file_name: str, data: dict[str, Any], require_description: bool
) -> None:
    for category, events in data.items():
        label = f"{file_name}.{category}"
        for event in events:
            if not isinstance(event, dict):
                raise OutputValidationError(f"{label} contains a non-object entry")
            if event.get("error"):
                raise OutputValidationError(
                    f"event page failed for {event.get('article_url', 'unknown URL')}"
                )

            required_keys = ["title", "article_url", "banner_url", "category"]
            if require_description:
                required_keys.append("description")
            for required_key in required_keys:
                value = event.get(required_key)
                if not isinstance(value, str) or not value.strip():
                    raise OutputValidationError(
                        f"{label} entry has invalid {required_key}"
                    )

            if not require_description and "description" in event:
                if not isinstance(event["description"], str):
                    raise OutputValidationError(
                        f"{label} entry has invalid description"
                    )

            if event["category"] != category:
                raise OutputValidationError(
                    f"{label} entry has mismatched category {event['category']!r}"
                )

            details = event.get("details")
            if not isinstance(details, dict):
                raise OutputValidationError(
                    f"{label} entry must contain a details object"
                )
            _validate_details(label, details)

            is_local_time = event.get("is_local_time")
            if not isinstance(is_local_time, bool):
                raise OutputValidationError(f"{label} entry must declare is_local_time")

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
                        f"{label} entry has invalid {time_key}; expected {time_type}"
                    )


def _validate_details(label: str, details: dict[str, Any]) -> None:
    """Validate detail sections.

    Section names are page-driven, so only the entry shapes are checked: plain
    strings (bonuses and legacy Pokémon lists) or Pokémon objects with a name.
    """
    for section, entries in details.items():
        if not isinstance(section, str) or not isinstance(entries, list):
            raise OutputValidationError(
                f"{label} entry has invalid details.{section!s}"
            )

        for entry in entries:
            if isinstance(entry, str):
                name = entry
            elif isinstance(entry, dict):
                name = entry.get("name")
            else:
                name = None

            if not isinstance(name, str) or not name.strip():
                raise OutputValidationError(
                    f"{label} entry has an invalid details.{section} item"
                )
