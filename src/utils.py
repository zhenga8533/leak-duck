import re
from datetime import datetime


def parse_cp_range(cp_string):
    """
    A helper function to parse a CP range string (e.g., "2190 - 2280").
    """
    if not cp_string or "-" not in cp_string:
        return None

    numbers = re.findall(r"\d+", cp_string)
    if len(numbers) == 2:
        return {"min": min(int(numbers[0]), int(numbers[1])), "max": max(int(numbers[0]), int(numbers[1]))}
    return None


def parse_pokemon_list(container):
    """
    A generic helper to parse lists of Pokémon from a containing element.
    It intelligently finds the name, shiny status, and asset URL.
    """
    pokemon_list = []
    pokemon_elements = container.select(".pokemon-card, .shadow-pokemon, .card")

    for p in pokemon_elements:
        name_element = p.find("span", class_="name") or p.find("p", class_="name")
        name = p.get("data-pokemon") or (name_element.get_text(strip=True) if name_element else "Unknown")

        is_shiny = p.find("svg", class_="shiny-icon") is not None

        asset_url_element = p.select_one("img.pokemon-image, .icon img, .boss-img img")
        asset_url = asset_url_element["src"] if asset_url_element else None

        if name != "Unknown":
            pokemon_list.append({"name": name, "shiny_available": is_shiny, "asset_url": asset_url})

    return pokemon_list


def process_time_data(date_element, time_element, is_local):
    print(f"Processing time data: is_local={is_local}, date_element={date_element}, time_element={time_element}")
    if is_local:
        if date_element and time_element:
            date_str = date_element.get_text(strip=True).replace(",", "").strip()
            time_str = time_element.get_text(strip=True).replace("at", "").replace("Local Time", "").strip()
            datetime_str = f"{date_str} {time_str}"
            try:
                # The format string matches the HTML's text content
                dt_object = datetime.strptime(datetime_str, "%A %B %d %Y %I:%M %p")
                return dt_object.isoformat()
            except ValueError:
                return None
    else:
        if date_element and "data-event-page-date" in date_element.attrs:
            iso_string = date_element["data-event-page-date"]
            try:
                # fromisoformat handles the standardized timestamp
                dt_object = datetime.fromisoformat(iso_string)
                return int(dt_object.timestamp())
            except (ValueError, TypeError):
                return None
    return None


def clean_banner_url(url):
    if not url:
        return None
    return re.sub(r"cdn-cgi/image/.*?\/(?=assets)", "", url)
