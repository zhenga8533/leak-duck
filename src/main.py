import json
from typing import Any

from src import scrapers
from src.archiver import EventArchiver
from src.paths import CONFIG_PATH


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_scraper(scraper_info: dict[str, Any]) -> None:
    scraper_class_name = scraper_info["class_name"]
    config = scraper_info["config"]

    print(f"--- Running {scraper_class_name} ---", flush=True)
    scraper_class = getattr(scrapers, scraper_class_name)

    scraper_args: dict[str, Any] = {
        "url": config["scrapers"][scraper_class_name]["url"],
        "file_name": config["scrapers"][scraper_class_name]["file_name"],
        "scraper_settings": config["scraper_settings"],
    }
    if scraper_class_name == "EventScraper":
        scraper_args["check_existing_events"] = config["scrapers"]["EventScraper"].get(
            "check_existing", False
        )
        scraper_args["github_user"] = config["github"]["user"]
        scraper_args["github_repo"] = config["github"]["repo"]

    scraper_instance = scraper_class(**scraper_args)
    scraper_instance.run()
    print(f"Successfully ran {scraper_class_name}", flush=True)


def main() -> None:
    print("=== Starting Leak Duck Scrapers ===", flush=True)
    config = load_config()
    print("Configuration loaded", flush=True)

    archiver = EventArchiver(
        user=config["github"]["user"], repo=config["github"]["repo"]
    )
    archiver.run()
    print("Event archiver completed", flush=True)

    scrapers_to_run: list[dict[str, Any]] = [
        {"class_name": name, "config": config}
        for name, settings in config["scrapers"].items()
        if settings["enabled"]
    ]

    failures: list[str] = []
    for scraper_info in scrapers_to_run:
        try:
            run_scraper(scraper_info)
        except Exception as e:
            class_name = scraper_info["class_name"]
            failures.append(f"{class_name}: {e}")
            print(f"✗ ERROR running {class_name}: {e}", flush=True)

    if failures:
        raise RuntimeError("One or more scrapers failed: " + "; ".join(failures))

    print("=== All scrapers finished ===", flush=True)


if __name__ == "__main__":
    main()
