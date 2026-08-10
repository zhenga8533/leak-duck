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

Archives are immutable point-in-time snapshots and are not rewritten to match newer schema versions, so consumers should treat them as compatible-but-not-identical to `events.json`:

- `description` is optional in legacy archived records; it is always present in `events.json`.
- Pokémon detail arrays (`details.features`, `spawns`, `eggs`, `raids`, `shiny`, `moves`) are plain name strings for events archived before July 2026 and Pokémon objects from July 2026 onward.

See the [archive compatibility notes](https://github.com/zhenga8533/leak-duck/wiki/API-Documentation#event-archives) for the full contract.
