import json
from pathlib import Path

from src.config.settings import DATA_DIR


REGISTRY_DIR = DATA_DIR / "registries"

ENTITY_TYPES_PATH = REGISTRY_DIR / "entity_types.json"
INFORMATION_TYPES_PATH = REGISTRY_DIR / "information_types.json"


class Registry:

    def load_entity_types(self):

        with ENTITY_TYPES_PATH.open(
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)

    def load_information_types(self):

        with INFORMATION_TYPES_PATH.open(
            "r",
            encoding="utf-8",
        ) as f:

            return json.load(f)

    def save_entity_types(self, entity_types):

        with ENTITY_TYPES_PATH.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                entity_types,
                f,
                ensure_ascii=False,
                indent=2,
            )

    def save_information_types(self, information_types):

        with INFORMATION_TYPES_PATH.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                information_types,
                f,
                ensure_ascii=False,
                indent=2,
            )