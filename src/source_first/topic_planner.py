from src.source_first.config import SourceFirstConfig
from src.source_first.schemas import TopicPlan


class TopicPlanner:
    def __init__(
        self,
        config: SourceFirstConfig | None = None,
    ):
        self.config = config or SourceFirstConfig()

    def plan(
        self,
        topic: str,
        language: str = "tr",
    ) -> TopicPlan:
        configured = self.config.topic_plan_for(topic)

        if configured is not None:
            return configured

        raise ValueError(
            "No source-first topic plan is configured for "
            f"{topic!r}. Add it to data/config/source_first.json."
        )
