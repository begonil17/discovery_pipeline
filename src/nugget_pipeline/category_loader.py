import json
from pathlib import Path


DEFAULT_CATEGORY_PATH = Path("config/categories.json")


def load_categories(path: str | Path = DEFAULT_CATEGORY_PATH) -> list[dict]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Category file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        categories = json.load(f)

    if not isinstance(categories, list):
        raise ValueError("Category file must contain a list of category objects.")

    return categories

