from scrapers import EggScraper, EventScraper, RaidBossScraper, ResearchScraper, RocketLineupScraper


def main():
    scrapers_to_run = [RaidBossScraper, ResearchScraper, RocketLineupScraper, EggScraper, EventScraper]

    seperator = "-" * 40
    print(seperator)

    for scraper_class in scrapers_to_run:
        scraper_instance = scraper_class()
        scraper_instance.run()
        print(seperator)


if __name__ == "__main__":
    main()
