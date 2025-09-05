# Leak Duck 🦆

[![Scrape Leek Duck Data](https://github.com/zhenga8533/leak-duck/actions/workflows/run_scrapers.yml/badge.svg)](https://github.com/zhenga8533/leak-duck/actions/workflows/run_scrapers.yml)
![Last Updated](https://img.shields.io/github/last-commit/zhenga8533/leak-duck/data)

A Python-based web scraper that automatically collects and updates Pokémon GO data from [leekduck.com](https://leekduck.com). This project uses GitHub Actions to run on a schedule and pushes the structured JSON data to a dedicated `data` branch.

---

## About The Project

This project provides a reliable, automated way to access up-to-date information for Pokémon GO. It scrapes the Leek Duck website for the latest details on:

- **Raid Bosses**: Current Pokémon in Tier 1, 3, 5, Mega, and Shadow Raids.
- **Events**: A categorized list of all current and upcoming in-game events.
- **Field Research**: All available research tasks and their possible rewards.
- **Team GO Rocket**: The complete lineups for Giovanni, the Leaders, and all Grunts.
- **Egg Pool**: The current list of Pokémon hatching from each egg distance.

The scraper is designed to be run automatically **every 12 hours** via a GitHub Actions workflow, ensuring the data is always fresh.

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

- Python 3.13
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
    python src/run.py
    ```

    When run locally, the script will create two folders in your project root: `html/` and `json/`. These folders are included in the `.gitignore` and will not be committed to your repository.

---

## Automation with GitHub Actions

This repository is configured to run the scraper automatically using GitHub Actions.

- **Workflow file:** `.github/workflows/run_scrapers.yml`
- **Trigger:** The workflow runs on a schedule (every 12 hours) and can also be triggered manually from the "Actions" tab in GitHub.
- **Process:**
  1.  The action checks out the `main` branch to get the latest scraper code.
  2.  It installs the Python dependencies.
  3.  It runs the `src/run.py` script, which generates the JSON files.
  4.  The action then checks out the `data` branch, adds the new JSON files, and commits them.
  5.  Finally, it pushes the updated data files directly to the `data` branch.

**Note:** For the GitHub Action to work, you must **manually create the `data` branch** as a clean, orphan branch in your repository first.

---

## Project Structure

```
leak-duck/
├── .github/
│   └── workflows/
│       └── run_scrapers.yml
├── src/
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py
│   │   ├── raid_boss_scraper.py
│   │   ├── research_scraper.py
│   │   ├── rocket_lineup_scraper.py
│   │   ├── egg_scraper.py
│   │   └── event_scraper.py
│   └── run.py
├── .gitignore
├── README.md
└── requirements.txt
```

---

## License

Distributed under the MIT License. You can create a file named `LICENSE` in your project root and add the contents of the MIT license to it.

---

## Acknowledgments

- All data is sourced from the fantastic resources at [leekduck.com](https://leekduck.com). This project is for educational purposes and is not affiliated with Leek Duck.
