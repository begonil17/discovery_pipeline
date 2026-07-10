import json
from pathlib import Path

from src.config.settings import DATA_DIR
from src.source_first.schemas import SourceProfile


SOURCE_REGISTRY_PATH = DATA_DIR / "registries" / "source_registry.json"


class SourceRegistry:
    def __init__(
        self,
        path: Path = SOURCE_REGISTRY_PATH,
    ):
        self.path = path

    def load_sources(self) -> list[SourceProfile]:
        with self.path.open(
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

        return [
            SourceProfile.model_validate(item)
            for item in data.get("sources", [])
        ]

    def sources_for_topic(
        self,
        topic: str,
    ) -> list[SourceProfile]:
        return [
            source
            for source in self.load_sources()
            if source.status == "active"
            and topic in source.supported_topics
        ]

    def save_sources(
        self,
        sources: list[SourceProfile],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "sources": [
                source.model_dump(mode="json")
                for source in sources
            ]
        }

        with self.path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )
