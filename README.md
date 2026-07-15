# Leak Duck 🦆

[![Scrape Leek Duck Data](https://github.com/zhenga8533/leak-duck/actions/workflows/run_scrapers.yml/badge.svg)](https://github.com/zhenga8533/leak-duck/actions/workflows/run_scrapers.yml)
![Last Updated](https://img.shields.io/github/last-commit/zhenga8533/leak-duck/data)

A Python-based web scraper that automatically collects and updates Pokémon GO data from [leekduck.com](https://leekduck.com). This project uses GitHub Actions to run on a schedule and pushes the structured JSON data to a dedicated `data` branch.

---

## About The Project

This project provides a reliable, automated way to access up-to-date information for Pokémon GO. It scrapes the Leek Duck website for the latest details on Raid Bosses, Events, Field Research, Team GO Rocket lineups, and the current Egg Pool. The scraper is designed to be run automatically **every hour** via a GitHub Actions workflow, ensuring the data is always fresh and reliable.

The scraped data is automatically committed and pushed to the `data` branch of this repository, making it easy to use as a free, simple API for your own projects.

---

## Features

- **Automated Scraping**: Runs automatically every hour using GitHub Actions.
- **Comprehensive Data**: Scrapes a wide range of Pokémon GO data, including:
  - **Raid Bosses**: Current Pokémon in all raid tiers.
  - **Events**: A categorized list of all current and upcoming in-game events.
  - **Field Research**: All available research tasks and their possible rewards.
  - **Team GO Rocket**: The complete lineups for Giovanni, Leaders, and Grunts.
  - **Egg Pool**: The current list of Pokémon hatching from each egg distance.
- **Data Archiving**: Automatically archives past events to a separate file for historical data.
- **Failure-safe**: Uses retries, atomic writes, output validation, and nonzero exits to prevent failed runs from publishing empty or partial datasets.
- **Organized**: A clean and modular project structure that is easy to understand and extend.

---

## API & Documentation

The raw JSON files can be used as simple, free API endpoints for your projects.

**➡️ For detailed information, visit the [Official Project Wiki](https://github.com/zhenga8533/leak-duck/wiki)**

The wiki includes a full breakdown of the data structure for each file, field descriptions, and direct links to the JSON endpoints.

---

## Data Output

The scraped data is automatically committed and pushed to the `data` branch of this repository.

**➡️ Browse the raw data files here: [https://github.com/zhenga8533/leak-duck/tree/data](https://github.com/zhenga8533/leak-duck/tree/data)**

The following files are generated:

- `raid_bosses.json` - All current Pokémon in Tier 1, 3, 5, Mega, and Shadow Raids.
- `research_tasks.json` - All available Field Research tasks and their possible rewards.
- `rocket_lineups.json` - The complete lineups for Team GO Rocket Leaders and Grunts.
- `egg_pool.json` - The current list of Pokémon hatching from each egg distance.
- `events.json`- All current and upcoming events.
- `archives/archive_YYYY.json` - Historical event data, organized by year.
  - _Note: Automated archiving of past events is handled by the script._

### Example Data (`raid_bosses.json`)

```json
{
  "Tier 5": [
    {
      "name": "Palkia",
      "tier": 5,
      "shiny_available": true,
      "cp_range": {
        "min": 2190,
        "max": 2280
      },
      "boosted_cp_range": {
        "min": 2737,
        "max": 2850
      },
      "types": ["Water", "Dragon"],
      "asset_url": "https://cdn.leekduck.com/assets/img/pokemon_icons/pm484.icon.png"
    }
  ]
}
```

---

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

- Python 3.12+
- pip

### Installation & Local Usage

1.  **Clone the repository:**

    ```sh
    git clone https://github.com/zhenga8533/leak-duck.git
    cd leak-duck
    ```

2.  **Create and activate a virtual environment:**

    ```sh
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required packages:**

    ```sh
    pip install -r requirements.txt
    ```

4.  **Run the scraper manually:**

    ```sh
    python -m src.main
    ```

    When run locally, the script will create two folders in your project root: `html/` and `json/`. These folders are included in the `.gitignore` and will not be committed to your repository.

    To write JSON somewhere else, set `LEAK_DUCK_OUTPUT_DIR` to the desired directory before running the command. An installed `leak-duck` command uses the current directory by default; `LEAK_DUCK_HOME` can set a different runtime root.

### Development Checks

Install the pinned development tools and run the same checks used by CI:

```sh
pip install -r requirements-dev.txt
ruff format --check .
ruff check .
python -m unittest discover -v
python -m compileall -q src tests
```

Use `ruff format .` to apply formatting. The tests are offline and cover parser selectors, output validation, fetch failures, and archive-preservation behavior.

---

## Automation with GitHub Actions

This repository is configured to run the scraper automatically using GitHub Actions.

- **Workflow file:** `.github/workflows/run_scrapers.yml`
- **Trigger:** The workflow runs on a schedule (every hour) and can also be triggered manually from the "Actions" tab in GitHub.
- **Process:**
  1.  The action checks out the `main` branch to get the latest scraper code.
  2.  It installs the pinned Python dependencies and runs the regression tests.
  3.  It runs the scraper into a temporary output directory.
  4.  Only after the complete run succeeds does it check out the `data` branch and copy the validated files.
  5.  It commits and pushes only when the generated data changed. Concurrent publishers are serialized to avoid races.

**Note:** For the GitHub Action to work, you must **manually create the `data` branch** as a clean, orphan branch in your repository first.

---

## Project Structure

```
leak-duck/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── run_scrapers.yml
│   ├── data-branch-readme.md
│   └── dependabot.yml
├── src/
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py
│   │   ├── raid_boss_scraper.py
│   │   ├── research_scraper.py
│   │   ├── rocket_lineup_scraper.py
│   │   ├── egg_scraper.py
│   │   ├── event_scraper.py
│   │   └── event_page_scraper.py
│   ├── __init__.py
│   ├── archiver.py
│   ├── config.json
│   ├── main.py
│   ├── paths.py
│   ├── validation.py
│   └── utils.py
├── tests/
│   ├── test_archiver.py
│   ├── test_scrapers.py
│   └── test_validation.py
├── .gitignore
├── LICENSE
├── pyproject.toml
├── README.md
├── requirements-dev.txt
└── requirements.txt
```

---

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Acknowledgments

- All data is sourced from the fantastic resources at [leekduck.com](https://leekduck.com).
- **Disclaimer**: This project is for educational purposes and is not affiliated with Leek Duck or Niantic.
