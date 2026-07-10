from src.fetcher.client import FetcherClient
from src.source_first.artifacts import ArtifactStore
from src.source_first.candidate_listing import CandidateLister
from src.source_first.config import SourceFirstConfig
from src.source_first.document_store import RawDocumentStore
from src.source_first.registry import SourceRegistry
from src.source_first.schemas import (
    CandidateItem,
    CollectionObjective,
    InformationNeed,
    NormalizedDocument,
    ScoredCandidate,
    SourceProfile,
)
from src.source_first.scoring import CandidateScorer
from src.source_first.topic_planner import TopicPlanner


def topic_planner_node(state):
    seed = state["seed"]
    planner = TopicPlanner()
    plan = planner.plan(
        topic=seed.title,
        language=seed.language,
    )

    ArtifactStore().save_json(
        plan.topic,
        "topic_plan.json",
        plan.model_dump(mode="json"),
    )

    print(
        f"Planned {len(plan.information_needs)} "
        f"information needs for {plan.topic}."
    )

    return {
        "topic_plan": plan,
        "errors": [],
    }


def source_registry_node(state):
    topic_plan = state["topic_plan"]
    sources = SourceRegistry().sources_for_topic(
        topic_plan.topic
    )

    ArtifactStore().save_json(
        topic_plan.topic,
        "sources.json",
        [
            source.model_dump(mode="json")
            for source in sources
        ],
    )

    print(
        f"Loaded {len(sources)} approved sources "
        f"for {topic_plan.topic}."
    )

    return {
        "sources": sources,
    }


def candidate_listing_node(state):
    config = SourceFirstConfig()
    listing_config = config.candidate_listing_config()
    topic_plan = state["topic_plan"]
    sources = state["sources"]
    artifact_store = ArtifactStore()

    checkpoint = artifact_store.load_json(
        topic_plan.topic,
        "candidates.json",
    )

    if checkpoint is not None:
        candidates = [
            CandidateItem.model_validate(item)
            for item in checkpoint
        ]

        print(
            f"Loaded {len(candidates)} candidate items "
            "from checkpoint."
        )

        return {
            "candidates": candidates,
        }

    lister = CandidateLister(
        max_results_per_source_need=listing_config.get(
            "max_results_per_source_need",
            10,
        ),
    )

    try:
        candidates = lister.list_candidates(
            topic_plan,
            sources,
        )
    except Exception as e:
        return {
            "candidates": [],
            "errors": [
                *state.get("errors", []),
                f"Candidate listing failed: {e}",
            ],
        }

    artifact_store.save_json(
        topic_plan.topic,
        "candidates.json",
        [
            candidate.model_dump(mode="json")
            for candidate in candidates
        ],
    )

    print(
        f"Listed {len(candidates)} candidate items "
        f"for {topic_plan.topic}."
    )

    return {
        "candidates": candidates,
    }


def scoring_node(state):
    config = SourceFirstConfig()
    topic_plan = state["topic_plan"]
    sources = state["sources"]
    candidates = state["candidates"]
    artifact_store = ArtifactStore()

    scored_checkpoint = artifact_store.load_json(
        topic_plan.topic,
        "scored_candidates.json",
    )
    selected_checkpoint = artifact_store.load_json(
        topic_plan.topic,
        "selected_candidates.json",
    )

    if (
        scored_checkpoint is not None
        and selected_checkpoint is not None
    ):
        scored = [
            ScoredCandidate.model_validate(item)
            for item in scored_checkpoint
        ]
        selected = [
            ScoredCandidate.model_validate(item)
            for item in selected_checkpoint
        ]

        print(
            f"Loaded {len(selected)} selected candidates "
            "from checkpoint."
        )

        return {
            "scored_candidates": scored,
            "selected_candidates": selected,
        }

    scorer = CandidateScorer(
        weights=config.scoring_weights(),
        selection_config=config.selection_config(),
    )

    scored = scorer.score(
        candidates,
        topic_plan,
        sources,
    )
    selected = scorer.select(
        scored,
        topic_plan,
    )

    artifact_store.save_json(
        topic_plan.topic,
        "scored_candidates.json",
        [
            item.model_dump(mode="json")
            for item in scored
        ],
    )
    artifact_store.save_json(
        topic_plan.topic,
        "selected_candidates.json",
        [
            item.model_dump(mode="json")
            for item in selected
        ],
    )

    print(
        f"Selected {len(selected)} candidates "
        f"for full extraction."
    )

    return {
        "scored_candidates": scored,
        "selected_candidates": selected,
    }


def _need_by_name(
    needs: list[InformationNeed],
) -> dict[str, InformationNeed]:
    return {
        need.name: need
        for need in needs
    }


def _source_by_id(
    sources: list[SourceProfile],
) -> dict[str, SourceProfile]:
    return {
        source.source_id: source
        for source in sources
    }


def fetcher_node(state):
    topic_plan = state["topic_plan"]
    selected = state["selected_candidates"]
    need_by_name = _need_by_name(topic_plan.information_needs)
    source_by_id = _source_by_id(state["sources"])
    fetcher = FetcherClient()
    store = RawDocumentStore()
    artifact_store = ArtifactStore()
    fetched_checkpoint = artifact_store.load_json(
        topic_plan.topic,
        "fetched_documents.json",
    )
    documents = [
        NormalizedDocument.model_validate(item)
        for item in (fetched_checkpoint or [])
    ]
    completed_ids = {
        document.candidate_id
        for document in documents
    }
    progress = artifact_store.load_json(
        topic_plan.topic,
        "fetch_progress.json",
    ) or {
        "completed_candidate_ids": [],
        "skipped_existing_candidate_ids": [],
        "failed": [],
    }
    progress.setdefault(
        "completed_candidate_ids",
        [],
    )
    progress.setdefault(
        "skipped_existing_candidate_ids",
        [],
    )
    progress.setdefault(
        "failed",
        [],
    )
    errors = list(state.get("errors", []))

    def append_unique(
        key: str,
        value: str,
    ):
        if value not in progress[key]:
            progress[key].append(value)

    def save_fetch_checkpoints():
        artifact_store.save_json(
            topic_plan.topic,
            "fetched_documents.json",
            [
                document.model_dump(mode="json")
                for document in documents
            ],
        )
        artifact_store.save_json(
            topic_plan.topic,
            "fetch_progress.json",
            progress,
        )

    for index, scored_candidate in enumerate(
        selected,
        start=1,
    ):
        candidate = scored_candidate.candidate

        if candidate.candidate_id in completed_ids:
            print(
                f"[{index}/{len(selected)}] "
                f"Already completed by checkpoint: {candidate.url}"
            )
            continue

        if store.exists(candidate):
            existing_document = store.load_for_candidate(candidate)

            if existing_document is not None:
                documents.append(existing_document)
                completed_ids.add(candidate.candidate_id)
                append_unique(
                    "completed_candidate_ids",
                    candidate.candidate_id
                )

            append_unique(
                "skipped_existing_candidate_ids",
                candidate.candidate_id,
            )
            save_fetch_checkpoints()

            print(
                f"[{index}/{len(selected)}] "
                f"Skipping already fetched: {candidate.url}"
            )
            continue

        source = source_by_id[candidate.source_id]
        need = need_by_name[candidate.information_need]
        objective = CollectionObjective(
            topic=topic_plan.topic,
            information_need=need.name,
            freshness_policy=need.freshness_policy,
            fields_to_preserve=[
                *source.collection_strategy.fields_to_preserve,
                *need.fields_to_preserve,
            ],
            content_type=need.name,
        )

        print(
            f"[{index}/{len(selected)}] Fetching "
            f"{candidate.information_need}: {candidate.url}"
        )

        document = fetcher.fetch(
            candidate.url,
            objective_context=objective.to_prompt_context(),
        )

        if document is None:
            errors.append(
                f"Fetch failed for {candidate.url}"
            )
            progress["failed"].append(
                {
                    "candidate_id": candidate.candidate_id,
                    "url": candidate.url,
                    "reason": "fetch returned no document",
                }
            )
            save_fetch_checkpoints()
            continue

        normalized = store.normalize(
            candidate,
            source,
            objective,
            document,
        )
        store.save(normalized)
        documents.append(normalized)
        completed_ids.add(candidate.candidate_id)
        append_unique(
            "completed_candidate_ids",
            candidate.candidate_id
        )
        save_fetch_checkpoints()

    print(
        f"Saved {len(documents)} normalized raw documents."
    )

    return {
        "documents": documents,
        "errors": errors,
    }
