import json
from dataclasses import dataclass
from pathlib import Path

from src.paths import CONFIG_PATH


@dataclass(frozen=True)
class ScraperSettings:
    retries: int = 3
    delay: float = 5
    timeout: float = 15
    cache_expiration_hours: float = 1


@dataclass(frozen=True)
class PublishedData:
    """The GitHub repository whose ``data`` branch hosts the published JSON."""

    user: str
    repo: str

    def url(self, path: str) -> str:
        return f"https://raw.githubusercontent.com/{self.user}/{self.repo}/data/{path}"


@dataclass(frozen=True)
class ScraperConfig:
    url: str
    file_name: str
    enabled: bool
    check_existing: bool = False


@dataclass(frozen=True)
class Config:
    published: PublishedData
    settings: ScraperSettings
    scrapers: dict[str, ScraperConfig]


def load_config(path: Path = CONFIG_PATH) -> Config:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    return Config(
        published=PublishedData(**raw["github"]),
        settings=ScraperSettings(**raw["scraper_settings"]),
        scrapers={
            name: ScraperConfig(**scraper) for name, scraper in raw["scrapers"].items()
        },
    )
