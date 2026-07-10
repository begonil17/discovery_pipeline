import json
from pathlib import Path
from typing import Any

from src.config.settings import DATA_DIR
from src.source_first.schemas import TopicPlan


SOURCE_FIRST_CONFIG_PATH = DATA_DIR / "config" / "source_first.json"


class SourceFirstConfig:
    def __init__(
        self,
        path: Path = SOURCE_FIRST_CONFIG_PATH,
    ):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        with self.path.open(
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)

    def topic_plan_for(self, topic: str) -> TopicPlan | None:
        for item in self.data.get("topic_plans", []):
            if item.get("topic") == topic:
                return TopicPlan.model_validate(item)

        return None

    def scoring_weights(self) -> dict[str, float]:
        return self.data.get("scoring_weights", {})

    def selection_config(self) -> dict[str, Any]:
        return self.data.get("selection", {})

    def candidate_listing_config(self) -> dict[str, Any]:
        return self.data.get("candidate_listing", {})
