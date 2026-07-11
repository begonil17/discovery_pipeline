from collections import defaultdict
from datetime import datetime, timezone

from src.source_first.schemas import (
    CandidateItem,
    CandidateScores,
    InformationNeed,
    ScoredCandidate,
    SourceProfile,
    TopicPlan,
)


DEFAULT_WEIGHTS = {
    "relevance": 0.22,
    "information_need_importance": 0.18,
    "freshness": 0.12,
    "popularity": 0.12,
    "source_authority": 0.16,
    "novelty": 0.12,
    "diversity": 0.08,
    "redundancy_penalty": 0.25,
    "cost_penalty": 0.08,
}


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 1.0,
) -> float:
    return max(low, min(high, value))


class CandidateScorer:
    def __init__(
        self,
        weights: dict[str, float] | None = None,
        selection_config: dict | None = None,
        known_urls: set[str] | None = None,
    ):
        self.weights = {
            **DEFAULT_WEIGHTS,
            **(weights or {}),
        }
        self.selection_config = selection_config or {}
        self.known_urls = known_urls or set()

    def _need_map(
        self,
        topic_plan: TopicPlan,
    ) -> dict[str, InformationNeed]:
        return {
            need.name: need
            for need in topic_plan.information_needs
        }

    def _source_map(
        self,
        sources: list[SourceProfile],
    ) -> dict[str, SourceProfile]:
        return {
            source.source_id: source
            for source in sources
        }

    def _popularity_scores(
        self,
        candidates: list[CandidateItem],
    ) -> dict[str, float]:
        grouped_values = defaultdict(list)
        raw_scores = {}

        for candidate in candidates:
            values = [
                value
                for value in candidate.popularity.values()
                if isinstance(value, (int, float))
            ]

            raw = max(values) if values else 0.0
            raw_scores[candidate.candidate_id] = raw
            grouped_values[candidate.source_id].append(raw)

        normalized = {}

        for candidate in candidates:
            values = grouped_values[candidate.source_id]
            min_value = min(values) if values else 0.0
            max_value = max(values) if values else 0.0
            raw = raw_scores[candidate.candidate_id]

            if max_value <= min_value:
                normalized[candidate.candidate_id] = (
                    0.0
                    if raw == 0.0
                    else 0.5
                )
            else:
                normalized[candidate.candidate_id] = (
                    raw - min_value
                ) / (max_value - min_value)

        return normalized

    def _freshness_score(
        self,
        candidate: CandidateItem,
        need: InformationNeed,
    ) -> float:
        policy = need.freshness_policy
        timestamp = candidate.updated_at or candidate.published_at

        if policy.freshness_type == "evergreen":
            return 0.7 if timestamp is None else 0.8

        if timestamp is None:
            return 0.25

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_days = max(
            0,
            (now - timestamp).days,
        )

        ttl_days = policy.ttl_days or 30

        return clamp(1.0 - (age_days / ttl_days))

    def score(
        self,
        candidates: list[CandidateItem],
        topic_plan: TopicPlan,
        sources: list[SourceProfile],
    ) -> list[ScoredCandidate]:
        needs = self._need_map(topic_plan)
        source_by_id = self._source_map(sources)
        popularity_by_id = self._popularity_scores(candidates)
        source_counts = defaultdict(int)
        scored = []

        for candidate in candidates:
            need = needs[candidate.information_need]
            source = source_by_id[candidate.source_id]

            tavily_score = candidate.metadata.get("tavily_score")
            relevance = clamp(float(tavily_score or 0.5))
            importance = clamp(need.importance / 5.0)
            freshness = self._freshness_score(candidate, need)
            popularity = popularity_by_id[candidate.candidate_id]
            authority = clamp(source.authority_score)
            novelty = 0.0 if candidate.url in self.known_urls else 1.0
            diversity = 1.0 / (1.0 + source_counts[source.source_id])
            redundancy_penalty = (
                1.0
                if candidate.url in self.known_urls
                else 0.0
            )
            cost_penalty = clamp(candidate.estimated_cost / 5.0)

            final_score = (
                relevance * self.weights["relevance"]
                + importance
                * self.weights["information_need_importance"]
                + freshness * self.weights["freshness"]
                + popularity * self.weights["popularity"]
                + authority * self.weights["source_authority"]
                + novelty * self.weights["novelty"]
                + diversity * self.weights["diversity"]
                - redundancy_penalty
                * self.weights["redundancy_penalty"]
                - cost_penalty * self.weights["cost_penalty"]
            )

            source_counts[source.source_id] += 1

            scored.append(
                ScoredCandidate(
                    candidate=candidate,
                    scores=CandidateScores(
                        relevance=relevance,
                        information_need_importance=importance,
                        freshness=freshness,
                        popularity=popularity,
                        source_authority=authority,
                        novelty=novelty,
                        diversity=diversity,
                        redundancy_penalty=redundancy_penalty,
                        cost_penalty=cost_penalty,
                        final_score=final_score,
                    ),
                )
            )

        return scored

    def _bucket_sort_key(
        self,
        item: ScoredCandidate,
        bucket: str,
    ) -> tuple[float, float]:
        scores = item.scores

        if bucket == "popular":
            return (
                scores.popularity,
                scores.final_score,
            )

        if bucket == "foundational":
            return (
                scores.source_authority
                + scores.information_need_importance
                + scores.relevance,
                scores.final_score,
            )

        return (
            scores.diversity
            + scores.novelty
            - scores.redundancy_penalty,
            scores.final_score,
        )

    def _configured_need_limit(
        self,
        topic_plan: TopicPlan,
        need: InformationNeed,
    ) -> int:

        by_topic = self.selection_config.get(
            "max_selected_items_by_topic",
            {},
        )
        topic_override = by_topic.get(topic_plan.topic)

        if isinstance(topic_override, int):
            return max(1, topic_override)

        if isinstance(topic_override, dict):
            need_override = topic_override.get(need.name)

            if need_override is None:
                need_override = topic_override.get("*")

            if isinstance(need_override, int):
                return max(1, need_override)

        global_override = self.selection_config.get(
            "max_selected_items_per_need",
        )

        if isinstance(global_override, int):
            return max(1, global_override)

        return need.max_selected_items

    def select(
        self,
        scored: list[ScoredCandidate],
        topic_plan: TopicPlan,
    ) -> list[ScoredCandidate]:
        allocation = self.selection_config.get(
            "allocation",
            {
                "popular": 0.6,
                "foundational": 0.25,
                "diverse": 0.15,
            },
        )

        max_share = self.selection_config.get(
            "max_source_share_per_need",
            0.6,
        )

        by_need = defaultdict(list)

        for item in scored:
            by_need[item.candidate.information_need].append(item)

        selected = []

        for need in topic_plan.information_needs:
            items = by_need[need.name]
            if not items:
                continue

            need_limit = self._configured_need_limit(
                topic_plan,
                need,
            )
            source_limit = max(1, int(need_limit * max_share))
            selected_ids = set()
            source_counts = defaultdict(int)

            for bucket, ratio in allocation.items():
                bucket_quota = max(
                    1,
                    int(round(need_limit * ratio)),
                )

                ordered = sorted(
                    items,
                    key=lambda item: self._bucket_sort_key(
                        item,
                        bucket,
                    ),
                    reverse=True,
                )

                for item in ordered:
                    if len(selected_ids) >= need_limit:
                        break

                    candidate = item.candidate

                    if candidate.candidate_id in selected_ids:
                        continue

                    if (
                        source_counts[candidate.source_id]
                        >= source_limit
                    ):
                        continue

                    item.selected = True
                    item.selection_bucket = bucket
                    item.selection_reason = (
                        f"Selected for {bucket} allocation."
                    )
                    selected_ids.add(candidate.candidate_id)
                    source_counts[candidate.source_id] += 1
                    selected.append(item)

                    if (
                        sum(
                            1
                            for selected_item in selected
                            if selected_item.candidate.information_need
                            == need.name
                            and selected_item.selection_bucket
                            == bucket
                        )
                        >= bucket_quota
                    ):
                        break

            if len(selected_ids) < need_limit:
                ordered = sorted(
                    items,
                    key=lambda item: item.scores.final_score,
                    reverse=True,
                )

                for item in ordered:
                    candidate = item.candidate

                    if len(selected_ids) >= need_limit:
                        break

                    if candidate.candidate_id in selected_ids:
                        continue

                    if (
                        source_counts[candidate.source_id]
                        >= source_limit
                    ):
                        continue

                    item.selected = True
                    item.selection_bucket = "fill"
                    item.selection_reason = (
                        "Selected to fill remaining need budget."
                    )
                    selected_ids.add(candidate.candidate_id)
                    source_counts[candidate.source_id] += 1
                    selected.append(item)

        return selected
