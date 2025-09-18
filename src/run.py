import concurrent.futures
import json

import scrapers
from archiver import EventArchiver


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def run_scraper(scraper_info):
    scraper_class_name = scraper_info["class_name"]
    config = scraper_info["config"]

    try:
        print(f"--- Running {scraper_class_name} ---")
        scraper_class = getattr(scrapers, scraper_class_name)

        # Prepare arguments for the scraper
        scraper_args = {
            "url": config["scrapers"][scraper_class_name]["url"],
            "file_name": config["scrapers"][scraper_class_name]["file_name"],
            "scraper_settings": config["scraper_settings"],
        }
        if scraper_class_name == "EventScraper":
            scraper_args["check_existing_events"] = config["scrapers"]["EventScraper"].get("check_existing", False)

        scraper_instance = scraper_class(**scraper_args)
        scraper_instance.run()
        return f"Successfully ran {scraper_class_name}"
    except Exception as e:
        return f"!!! ERROR running {scraper_class_name}: {e} !!!"


def main():
    config = load_config()

    archiver = EventArchiver(user=config["github"]["user"], repo=config["github"]["repo"])
    archiver.run()

    scrapers_to_run = [
        {"class_name": name, "config": config} for name, settings in config["scrapers"].items() if settings["enabled"]
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(run_scraper, scrapers_to_run)
        for result in results:
            print(result)

    print("--- All scrapers finished ---")


if __name__ == "__main__":
    main()
