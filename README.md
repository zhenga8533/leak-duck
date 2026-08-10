# Leak Duck Data Branch 🦆

This branch contains automatically generated Pokémon GO data sourced from [leekduck.com](https://leekduck.com). The data is updated every hour by an automated workflow. For information about the scraper, visit the [main repository](https://github.com/zhenga8533/leak-duck).

![Last Updated](https://img.shields.io/github/last-commit/zhenga8533/leak-duck/data)

## How to Use This Data

The raw JSON file URLs can be used as simple, free API endpoints. See the [official API documentation](https://github.com/zhenga8533/leak-duck/wiki/API-Documentation) for field descriptions and complete data structures.

## Data Files

- **Raids:** `https://raw.githubusercontent.com/zhenga8533/leak-duck/data/raid_bosses.json`
- **Events:** `https://raw.githubusercontent.com/zhenga8533/leak-duck/data/events.json`
- **Research:** `https://raw.githubusercontent.com/zhenga8533/leak-duck/data/research_tasks.json`
- **Rocket Lineups:** `https://raw.githubusercontent.com/zhenga8533/leak-duck/data/rocket_lineups.json`
- **Egg Pool:** `https://raw.githubusercontent.com/zhenga8533/leak-duck/data/egg_pool.json`
- **Event Archives:** [browse yearly archives](https://github.com/zhenga8533/leak-duck/tree/data/archives)

## Event Archives

Ended events are moved from `events.json` into `archives/archive_YYYY.json`. Automated archiving began on **September 19, 2025**; events that ended before that date are not included.

Archives were rebuilt from their original Leek Duck pages on **August 10, 2026**, so every archived record now uses the same schema as `events.json`:

- Pokémon detail arrays (`details.features`, `spawns`, `eggs`, `raids`, `shiny`, `moves`) are arrays of Pokémon objects throughout. The legacy plain-string format is no longer present.
- `description` is present except for a small number of events whose Leek Duck page no longer exists, so treat it as optional when reading archives.

See the [archive compatibility notes](https://github.com/zhenga8533/leak-duck/wiki/API-Documentation#event-archives) for the full contract.
