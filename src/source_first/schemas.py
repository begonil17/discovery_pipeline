from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


FreshnessType = Literal[
    "evergreen",
    "recent",
    "short_ttl",
    "versioned",
]

CollectionMethod = Literal[
    "tavily_search",
    "rss",
    "sitemap",
    "configured_listing",
]

CandidateStatus = Literal[
    "listed",
    "selected",
    "fetched",
    "skipped",
    "failed",
]

DocumentStatus = Literal[
    "active",
    "superseded",
    "failed",
]


class FreshnessPolicy(BaseModel):
    freshness_type: FreshnessType = "evergreen"
    ttl_days: int | None = None
    newer_supersedes_older: bool = False


class InformationNeed(BaseModel):
    name: str
    description: str = ""
    importance: float = Field(default=3.0, ge=0.0, le=5.0)
    freshness_policy: FreshnessPolicy = Field(
        default_factory=FreshnessPolicy
    )
    desired_coverage: str = "balanced"
    max_selected_items: int = Field(default=5, ge=1)
    fields_to_preserve: list[str] = Field(default_factory=list)


class TopicPlan(BaseModel):
    topic: str
    language: str = "tr"
    information_needs: list[InformationNeed] = Field(
        default_factory=list
    )


class SourceWatermark(BaseModel):
    last_successful_fetch: datetime | None = None
    last_seen_item_id: str | None = None
    last_seen_publication_time: datetime | None = None


class CollectionStrategy(BaseModel):
    method: CollectionMethod = "tavily_search"
    entry_points: list[str] = Field(default_factory=list)
    search_templates: list[str] = Field(default_factory=list)
    listing_pages: list[str] = Field(default_factory=list)
    rss_feeds: list[str] = Field(default_factory=list)
    sitemap_urls: list[str] = Field(default_factory=list)
    pagination: dict[str, Any] = Field(default_factory=dict)
    item_url_patterns: list[str] = Field(default_factory=list)
    date_selectors: list[str] = Field(default_factory=list)
    popularity_selectors: list[str] = Field(default_factory=list)
    fields_to_preserve: list[str] = Field(default_factory=list)
    max_candidates: int = Field(default=20, ge=1)


class SourceProfile(BaseModel):
    source_id: str
    domain: str
    name: str
    supported_topics: list[str] = Field(default_factory=list)
    supported_information_needs: list[str] = Field(default_factory=list)
    language: str = "tr"
    authority_score: float = Field(default=0.5, ge=0.0, le=1.0)
    update_frequency: str = "unknown"
    popularity_metric: str | None = None
    suitable_for: list[FreshnessType] = Field(default_factory=list)
    collection_strategy: CollectionStrategy = Field(
        default_factory=CollectionStrategy
    )
    watermark: SourceWatermark = Field(
        default_factory=SourceWatermark
    )
    status: Literal["active", "inactive"] = "active"
    notes: str = ""

    def supports_need(
        self,
        topic: str,
        information_need: str,
    ) -> bool:
        return (
            self.status == "active"
            and topic in self.supported_topics
            and information_need
            in self.supported_information_needs
        )


class CandidateItem(BaseModel):
    candidate_id: str
    topic: str
    information_need: str
    source_id: str
    source_domain: str
    title: str
    url: str
    published_at: datetime | None = None
    updated_at: datetime | None = None
    popularity: dict[str, float] = Field(default_factory=dict)
    category: str | None = None
    estimated_cost: float = 1.0
    status: CandidateStatus = "listed"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateScores(BaseModel):
    relevance: float = 0.0
    information_need_importance: float = 0.0
    freshness: float = 0.0
    popularity: float = 0.0
    source_authority: float = 0.0
    novelty: float = 0.0
    diversity: float = 0.0
    redundancy_penalty: float = 0.0
    cost_penalty: float = 0.0
    final_score: float = 0.0


class ScoredCandidate(BaseModel):
    candidate: CandidateItem
    scores: CandidateScores
    selection_bucket: str | None = None
    selected: bool = False
    selection_reason: str = ""


class CollectionObjective(BaseModel):
    topic: str
    information_need: str
    freshness_policy: FreshnessPolicy
    fields_to_preserve: list[str] = Field(default_factory=list)
    content_type: str = "general"

    def to_prompt_context(self) -> str:
        fields = ", ".join(self.fields_to_preserve) or "general facts"
        return (
            f"Topic: {self.topic}\n"
            f"Information need: {self.information_need}\n"
            f"Content type: {self.content_type}\n"
            f"Freshness type: {self.freshness_policy.freshness_type}\n"
            f"Fields to preserve: {fields}"
        )


class NormalizedDocument(BaseModel):
    document_id: str
    topic: str
    information_need: str
    source: str
    source_id: str
    source_url: str
    title: str
    text: str
    published_at: datetime | None = None
    updated_at: datetime | None = None
    fetched_at: datetime
    popularity_metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str
    status: DocumentStatus = "active"
    candidate_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
