import concurrent.futures

from archiver import EventArchiver
from scrapers import EggScraper, EventScraper, RaidBossScraper, ResearchScraper, RocketLineupScraper


def run_scraper(scraper_class):
    try:
        print(f"--- Running {scraper_class.__name__} ---")
        scraper_instance = scraper_class()
        scraper_instance.run()
        return f"Successfully ran {scraper_class.__name__}"
    except Exception as e:
        return f"!!! ERROR running {scraper_class.__name__}: {e} !!!"


def main():
    archiver = EventArchiver(user="zhenga8533", repo="leak-duck")
    archiver.run()

    scrapers_to_run = [RaidBossScraper, ResearchScraper, RocketLineupScraper, EggScraper, EventScraper]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(run_scraper, scrapers_to_run)
        for result in results:
            print(result)

    print("--- All scrapers finished ---")


if __name__ == "__main__":
    main()
