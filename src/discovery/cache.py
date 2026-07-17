import json
import re
from pathlib import Path

from src.config.settings import CACHE_DIR
from src.persistence.manifest import atomic_write_json
from src.schemas.entity import Entity


def seed_cache_filename(seed) -> str:
    safe_title = re.sub(
        r'[<>:"/\\|?*]',
        "",
        seed.title,
    )
    safe_title = re.sub(
        r"\s+",
        "_",
        safe_title.strip(),
    )
    return f"{safe_title}_depth_{seed.max_depth}_limit_{seed.entity_limit}.json"


def stage_cache_path(seed, stage: str) -> Path:
    return CACHE_DIR / stage / seed_cache_filename(seed)


def load_entities_from_stage(seed, stage: str) -> list[Entity] | None:
    path = stage_cache_path(seed, stage)

    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if not isinstance(data, list):
        return None

    return [
        Entity.model_validate(item)
        for item in data
        if isinstance(item, dict)
    ]


def save_entities_to_stage(seed, stage: str, entities: list[Entity]) -> Path:
    path = stage_cache_path(seed, stage)
    atomic_write_json(
        path,
        [
            entity.model_dump()
            for entity in entities
        ],
    )
    return path
