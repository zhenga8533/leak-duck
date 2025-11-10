import json
import os
import sys
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import scrapers
from src.archiver import EventArchiver


def load_config() -> dict[str, Any]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, "r") as f:
        return json.load(f)


def run_scraper(scraper_info: dict[str, Any]) -> str:
    scraper_class_name = scraper_info["class_name"]
    config = scraper_info["config"]

    try:
        print(f"--- Running {scraper_class_name} ---", flush=True)
        scraper_class = getattr(scrapers, scraper_class_name)

        scraper_args: dict[str, Any] = {
            "url": config["scrapers"][scraper_class_name]["url"],
            "file_name": config["scrapers"][scraper_class_name]["file_name"],
            "scraper_settings": config["scraper_settings"],
        }
        if scraper_class_name == "EventScraper":
            scraper_args["check_existing_events"] = config["scrapers"][
                "EventScraper"
            ].get("check_existing", False)
            scraper_args["github_user"] = config["github"]["user"]
            scraper_args["github_repo"] = config["github"]["repo"]

        scraper_instance = scraper_class(**scraper_args)
        scraper_instance.run()
        return f"Successfully ran {scraper_class_name}"
    except Exception as e:
        return f"✗ ERROR running {scraper_class_name}: {e}"


def main():
    print("=== Starting Leak Duck Scrapers ===", flush=True)
    config = load_config()
    print("Configuration loaded", flush=True)

    try:
        archiver = EventArchiver(
            user=config["github"]["user"], repo=config["github"]["repo"]
        )
        archiver.run()
        print("Event archiver completed", flush=True)
    except Exception as e:
        print(f"✗ ERROR in Event Archiver: {e}", flush=True)

    scrapers_to_run: list[dict[str, Any]] = [
        {"class_name": name, "config": config}
        for name, settings in config["scrapers"].items()
        if settings["enabled"]
    ]

    for scraper in scrapers_to_run:
        result = run_scraper(scraper)
        print(result, flush=True)

    print("=== All scrapers finished ===", flush=True)


if __name__ == "__main__":
    main()
