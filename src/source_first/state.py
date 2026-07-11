from typing import TypedDict

from src.schemas.seed import Seed
from src.source_first.schemas import (
    CandidateItem,
    NormalizedDocument,
    ScoredCandidate,
    SourceProfile,
    TopicPlan,
)


class SourceFirstState(TypedDict, total=False):
    seed: Seed
    topic_plan: TopicPlan
    sources: list[SourceProfile]
    candidates: list[CandidateItem]
    scored_candidates: list[ScoredCandidate]
    selected_candidates: list[ScoredCandidate]
    documents: list[NormalizedDocument]
    errors: list[str]
    document_budget: int | None
    run_document_budget: int | None
    run_seed_count: int
    run_seed_index: int
