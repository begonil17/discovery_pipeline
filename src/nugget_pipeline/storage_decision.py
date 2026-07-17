import json

from src.nugget_pipeline.config import NUGGET_QA_MODEL
from src.nugget_pipeline.llm.client import generate_json
from src.nugget_pipeline.schemas import StorageDecision
from src.nugget_pipeline.llm.schemas import STORAGE_DECISION_SCHEMA


FALLBACK_STORAGE_REASON = (
    "Storage decision produced no kept nuggets; preserved important candidates as fallback."
)
MISSING_DECISION_REASON = (
    "No storage decision returned for this nugget; preserved due to high importance."
)


def nugget_importance(nugget: dict) -> int:
    try:
        return int(nugget.get("importance", 0))
    except (TypeError, ValueError):
        return 0


def with_storage_fields(
    nugget: dict,
    storage_action: str,
    storage_reason: str,
    detail_level: str = "medium",
    questions_per_nugget: int = 2,
) -> dict:
    updated = dict(nugget)
    updated["storage_action"] = storage_action
    updated["storage_reason"] = storage_reason
    updated["detail_level"] = detail_level
    updated["questions_per_nugget"] = questions_per_nugget
    return updated


def fallback_keep_top_candidates(candidate_nuggets: list[dict]) -> list[dict]:
    fallback_limit = min(5, len(candidate_nuggets))
    fallback_candidates = sorted(
        candidate_nuggets,
        key=nugget_importance,
        reverse=True,
    )[:fallback_limit]

    print(
        "[storage_decision] WARNING: Storage decision kept 0 nuggets "
        f"from {len(candidate_nuggets)} candidates. "
        f"Fallback keeping {len(fallback_candidates)}."
    )

    return [
        with_storage_fields(
            nugget,
            storage_action="fallback_keep",
            storage_reason=FALLBACK_STORAGE_REASON,
        )
        for nugget in fallback_candidates
    ]


def decide_nugget_storage(
    article_title: str,
    candidate_nuggets: list[dict],
    existing_nuggets: list[dict] | None = None,
) -> list[dict]:
    existing_nuggets = existing_nuggets or []
    candidate_ids = [
        nugget.get("nugget_id")
        for nugget in candidate_nuggets
        if nugget.get("nugget_id")
    ]
    candidate_by_id = {
        nugget.get("nugget_id"): nugget
        for nugget in candidate_nuggets
        if nugget.get("nugget_id")
    }

    print(
        "[storage_decision] Candidate nuggets entering storage decision: "
        f"{len(candidate_nuggets)}"
    )
    print(f"[storage_decision] Candidate nugget IDs: {candidate_ids}")

    prompt = f"""
You are deciding which extracted knowledge nuggets should be stored in a limited-memory Turkish QA dataset.

Article title: {article_title}

Existing stored nuggets:
{json.dumps(existing_nuggets, ensure_ascii=False, indent=2)}

Candidate nuggets:
{json.dumps(candidate_nuggets, ensure_ascii=False, indent=2)}

Candidate nugget IDs you may refer to:
{json.dumps(candidate_ids, ensure_ascii=False, indent=2)}

For each candidate nugget, decide how it should be stored.
Return one decision per candidate nugget.
Use only nugget_id values from the candidate nuggets.
Do not invent, rewrite, or normalize nugget_id values.

Possible actions:
- keep_full: important and useful; store with full detail
- keep_compressed: useful but not central; store in shorter form
- merge: overlaps with existing/candidate nugget; rewrite as one better final_text
- skip: too trivial, redundant, overly specific, controversial, or low value

Decision criteria:
- Prefer broad, stable, useful knowledge for everyday Turkish users.
- Avoid storing duplicate or near-duplicate facts.
- Avoid controversial, political, polarizing, adult, illegal, or sensitive medical/legal/financial advice.
- Higher importance should usually receive more detail, but do not rely only on importance.
- final_text must be Turkish.
- final_text must be atomic: one fact only.
- questions_per_nugget:
  - high detail: 3
  - medium detail: 2
  - low detail: 1
  - skip: 0

"""

    raw = generate_json(
        prompt=prompt,
        model_name=NUGGET_QA_MODEL,
        schema=STORAGE_DECISION_SCHEMA
    )

    if not isinstance(raw, list):
        print(
            "[storage_decision] WARNING: LLM storage decision did not return "
            f"a list. Got {type(raw).__name__}."
        )
        raw = []

    decisions = []
    for item in raw:
        try:
            decisions.append(StorageDecision(**item))
        except Exception as exc:
            print(
                "[storage_decision] WARNING: Ignoring invalid storage decision "
                f"{item!r}. Error: {exc}"
            )

    print(f"[storage_decision] LLM returned {len(decisions)} decisions.")
    print(
        "[storage_decision] Decision actions: "
        f"{[decision.action for decision in decisions]}"
    )
    print(
        "[storage_decision] Decision nugget IDs: "
        f"{[decision.nugget_id for decision in decisions]}"
    )

    final_nuggets = []
    decided_candidate_ids = set()
    kept_candidate_ids = set()

    for decision in decisions:
        original = candidate_by_id.get(decision.nugget_id)

        if original is None:
            print(
                "[storage_decision] WARNING: Decision nugget_id not found "
                f"in candidate_nuggets: {decision.nugget_id}"
            )
            continue

        decided_candidate_ids.add(decision.nugget_id)

        if decision.action == "skip":
            print(
                "[storage_decision] Skipped nugget "
                f"{decision.nugget_id}: {decision.reason}"
            )
            continue

        if decision.nugget_id in kept_candidate_ids:
            print(
                "[storage_decision] WARNING: Duplicate kept decision ignored "
                f"for nugget_id: {decision.nugget_id}"
            )
            continue

        updated = dict(original)
        updated["text"] = decision.final_text or original.get("text", "")
        updated["detail_level"] = decision.detail_level
        updated["questions_per_nugget"] = decision.questions_per_nugget
        updated["storage_action"] = decision.action
        updated["storage_reason"] = decision.reason

        final_nuggets.append(updated)
        kept_candidate_ids.add(decision.nugget_id)

    for candidate in candidate_nuggets:
        nugget_id = candidate.get("nugget_id")

        if nugget_id in decided_candidate_ids:
            continue

        if nugget_importance(candidate) >= 7:
            print(
                "[storage_decision] WARNING: Missing decision for high-importance "
                f"nugget {nugget_id}; preserving with fallback."
            )
            final_nuggets.append(
                with_storage_fields(
                    candidate,
                    storage_action="fallback_missing_decision",
                    storage_reason=MISSING_DECISION_REASON,
                )
            )
            if nugget_id:
                kept_candidate_ids.add(nugget_id)
        else:
            print(
                "[storage_decision] Skipped nugget "
                f"{nugget_id}: no storage decision returned and importance "
                f"{nugget_importance(candidate)} < 7."
            )

    if not final_nuggets and candidate_nuggets:
        final_nuggets = fallback_keep_top_candidates(candidate_nuggets)

    return final_nuggets


