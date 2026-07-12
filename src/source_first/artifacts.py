import json
from pathlib import Path
from typing import Any

from src.config.settings import DATA_DIR
from src.fetcher.saver import sanitize_filename


ARTIFACT_DIR = DATA_DIR / "source_first_runs"


def safe_name(name: str) -> str:
    return sanitize_filename(name)


class ArtifactStore:
    def __init__(
        self,
        root: Path = ARTIFACT_DIR,
    ):
        self.root = root

    def topic_dir(
        self,
        topic: str,
    ) -> Path:
        path = self.root / safe_name(topic)
        path.mkdir(
            parents=True,
            exist_ok=True,
        )
        return path

    def path_for(
        self,
        topic: str,
        name: str,
    ) -> Path:
        return self.topic_dir(topic) / name

    def has_json(
        self,
        topic: str,
        name: str,
    ) -> bool:
        return self.path_for(
            topic,
            name,
        ).is_file()

    def load_json(
        self,
        topic: str,
        name: str,
    ) -> Any | None:
        path = self.path_for(
            topic,
            name,
        )

        if not path.is_file():
            return None

        with path.open(
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)

    def save_json(
        self,
        topic: str,
        name: str,
        data: Any,
    ) -> Path:
        path = self.path_for(
            topic,
            name,
        )
        temp_path = path.with_name(f"{path.name}.tmp")

        with temp_path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        temp_path.replace(path)

        return path
