import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().with_name("config.json")


def runtime_root() -> Path:
    """Return the checkout root, or the current directory when installed."""
    configured_root = os.getenv("LEAK_DUCK_HOME")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    if (PROJECT_ROOT / ".git").exists():
        return PROJECT_ROOT
    return Path.cwd().resolve()


HTML_DIR = runtime_root() / "html"


def data_dir() -> Path:
    """Return the data output directory, independent of the current directory."""
    configured_dir = os.getenv("LEAK_DUCK_OUTPUT_DIR")
    if configured_dir:
        return Path(configured_dir).expanduser().resolve()
    root = runtime_root()
    return root if os.getenv("CI") else root / "json"
