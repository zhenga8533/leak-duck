from archiver import EventArchiver
from scrapers import EggScraper, EventScraper, RaidBossScraper, ResearchScraper, RocketLineupScraper


def main():
    archiver = EventArchiver(user="zhenga8533", repo="leak-duck")
    archiver.run()

    scrapers_to_run = [RaidBossScraper, ResearchScraper, RocketLineupScraper, EggScraper, EventScraper]

    for scraper_class in scrapers_to_run:
        try:
            print(f"--- Running {scraper_class.__name__} ---")
            scraper_instance = scraper_class()
            scraper_instance.run()
        except Exception as e:
            print(f"!!! ERROR running {scraper_class.__name__}: {e} !!!")

    print("--- All scrapers finished ---")


if __name__ == "__main__":
    main()
