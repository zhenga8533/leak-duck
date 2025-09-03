# Leak Duck 🦆

A Python-based web scraper that automatically collects and updates Pokémon GO data from [leekduck.com](https://leekduck.com). This project uses GitHub Actions to run on a schedule and pushes the structured JSON data to a dedicated `data` branch.

---

## About The Project

This project was created to provide a reliable, automated way to access up-to-date information for Pokémon GO. It scrapes the Leek Duck website for the latest details on:

- **Raid Bosses**: Current Pokémon in Raids.
- **Events**: A categorized list of all current and upcoming in-game events.
- **Field Research**: All available research tasks and their possible rewards.
- **Team GO Rocket**: The complete lineups for Giovanni, the Leaders, and all Grunts.
- **Egg Pool**: The current list of Pokémon hatching from each egg distance.

The scraper is designed to be run automatically every hour via a GitHub Actions workflow, ensuring the data is always fresh.

---

## Data Output

The scraped data is automatically committed and pushed to the `data` branch of this repository as a set of JSON files.

**➡️ Browse the data here: [https://github.com/zhenga8533/leak-duck/tree/data](https://www.google.com/search?q=https://github.com/zhenga8533/leak-duck/tree/data)**

The following files are generated:

- `raid_bosses.json`
- `events.json`
- `research_tasks.json`
- `rocket_lineups.json`
- `egg_pool.json`

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

- Python 3.10 or later
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

    When run locally, the script will create two folders in your project root: `html/` (containing the raw HTML of each scraped page) and `json/` (containing the generated data files). These folders are included in the `.gitignore` and will not be committed to your repository.

---

## Automation with GitHub Actions

This repository is configured to run the scraper automatically using GitHub Actions.

- **Workflow file:** `.github/workflows/run_scrapers.yml`
- **Trigger:** The workflow runs on a schedule (every hour at the top of the hour) and can also be triggered manually from the "Actions" tab in GitHub.
- **Process:**
  1.  The action checks out the `main` branch to get the latest scraper code.
  2.  It installs the Python dependencies.
  3.  It runs the `src/run.py` script, which generates the JSON files in the workspace root.
  4.  The action then checks out the `data` branch, adds the new JSON files, and commits them.
  5.  Finally, it pushes the updated data files directly to the `data` branch.

**Note:** For the GitHub Action to work, you must **manually create the `data` branch** in your repository first.

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

Distributed under the MIT License. See `LICENSE` for more information.

---

## Acknowledgments

- All data is sourced from the fantastic resources at [leekduck.com](https://leekduck.com). This project is for educational purposes and is not affiliated with Leek Duck.
