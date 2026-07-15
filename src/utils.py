import json
import os
import re
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from bs4.element import Tag


def save_html(content: str, path: str | Path) -> None:
    """Utility function to save HTML content to a specified path."""
    if not os.getenv("CI"):
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved raw HTML to {output_path}")


def write_json_atomic(path: str | Path, data: Any) -> None:
    """Write JSON atomically so interrupted runs cannot leave truncated files."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(data, temporary_file, ensure_ascii=False, indent=4)
            temporary_file.write("\n")
        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def parse_cp_range(cp_string: str) -> dict[str, int] | None:
    """
    A helper function to parse a CP range string (e.g., "2190 - 2280").
    """
    if not cp_string or "-" not in cp_string:
        return None

    numbers = re.findall(r"\d+", cp_string)
    if len(numbers) == 2:
        return {
            "min": min(int(numbers[0]), int(numbers[1])),
            "max": max(int(numbers[0]), int(numbers[1])),
        }
    return None


def parse_pokemon_list(container: Tag) -> list[dict[str, Any]]:
    """
    A generic helper to parse lists of Pokémon from a containing element.
    It intelligently finds the name, shiny status, and asset URL.
    """
    pokemon_list = []
    pokemon_elements = container.select(".pokemon-card, .shadow-pokemon, .card")

    for p in pokemon_elements:
        name_element = p.find("span", class_="name") or p.find("p", class_="name")
        name = p.get("data-pokemon") or (
            name_element.get_text(strip=True) if name_element else "Unknown"
        )

        is_shiny = p.find("svg", class_="shiny-icon") is not None

        asset_url_element = p.select_one("img.pokemon-image, .icon img, .boss-img img")
        asset_url = (
            asset_url_element["src"]
            if asset_url_element and asset_url_element.has_attr("src")
            else None
        )

        if name != "Unknown":
            pokemon_list.append(
                {"name": name, "shiny_available": is_shiny, "asset_url": asset_url}
            )

    return pokemon_list


def process_time_data(
    date_element: Tag | None, time_element: Tag | None, is_local: bool
) -> str | int | None:
    if is_local:
        if date_element and time_element:
            raw_date_str = date_element.get_text(strip=True)
            raw_time_str = time_element.get_text(strip=True)
            date_str = re.sub(r"\s+", " ", raw_date_str).replace(",", "").strip()
            time_str = (
                re.sub(r"\s+", " ", raw_time_str)
                .replace("at", "")
                .replace("Local Time", "")
                .strip()
            )
            datetime_str = f"{date_str} {time_str}"
            try:
                dt_object = datetime.strptime(datetime_str, "%A %B %d %Y %I:%M %p")
                return dt_object.isoformat()
            except ValueError:
                return None
    else:
        if date_element and "data-event-page-date" in date_element.attrs:
            iso_string = date_element["data-event-page-date"]
            try:
                dt_object = datetime.fromisoformat(str(iso_string))
                return int(dt_object.timestamp())
            except (ValueError, TypeError):
                return None
    return None


def parse_feed_datetime(value: str | None) -> str | int | None:
    """
    Parses an ISO 8601 timestamp from the official leekduck.com/feeds/events.json feed.

    Naive timestamps (no offset) represent local event time and are kept as an
    ISO string; offset-aware timestamps are converted to unix time, matching the
    schema produced by process_time_data() for HTML-scraped dates.
    """
    if not value:
        return None
    try:
        dt_object = datetime.fromisoformat(value)
    except ValueError:
        return None

    if dt_object.tzinfo is not None:
        return int(dt_object.timestamp())
    return dt_object.isoformat()


def clean_banner_url(url: str | None) -> str | None:
    if not url:
        return None
    return re.sub(r"cdn-cgi/image/.*?\/(?=assets)", "", url)
