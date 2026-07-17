import time

from src.planner.prompt import build_prompt
from src.planner.registry import Registry
from src.planner.schemas import PlannerDecision
from src.config.settings import PLANNER_MODEL
from src.discovery.cache import (
    load_entities_from_stage,
    save_entities_to_stage,
)
from src.llm.client import LLMClient


def planner_node(state):

    print("\n" + "=" * 80)
    print("Starting Knowledge Planner")
    print("=" * 80)

    registry = Registry()

    client = LLMClient()

    seed = state["seed"]

    if not state.get("refresh_planner", False):
        cached_planned_entities = load_entities_from_stage(
            seed,
            "planned",
        )

        if cached_planned_entities is not None:
            cached_rejected_entities = (
                load_entities_from_stage(
                    seed,
                    "rejected",
                )
                or []
            )
            print(
                "Loaded planner results from cache "
                f"({len(cached_planned_entities)} included, "
                f"{len(cached_rejected_entities)} rejected)."
            )
            return {
                "discovered_entities": cached_planned_entities,
                "rejected_entities": cached_rejected_entities,
            }

    entities = state["discovered_entities"]

    print(f"Planning {len(entities)} entities...\n")

    planned_entities = []
    rejected_entities = []
    planned_count = 0

    total_start = time.time()

    for i, entity in enumerate(entities, start=1):

        print("-" * 80)
        print(f"[{i}/{len(entities)}] {entity.title}")

        prompt_start = time.time()

        prompt = build_prompt(
            entity=entity,
            seed=seed,
            registry=registry,
        )

        print(
            f"✓ Prompt built "
            f"({time.time() - prompt_start:.2f}s)"
        )

        print("→ Calling Gemini...")

        llm_start = time.time()

        try:

            decision = client.generate_structured(
                prompt=prompt,
                model_name=PLANNER_MODEL,
                output_model=PlannerDecision,
            )

        except Exception as e:

            print(f"✗ Failed on {entity.title}")
            print(e)
            print(
                "Keeping the entity with a permissive "
                "fallback plan."
            )

            decision = PlannerDecision(
                include=True,
                expand=True,
                entity_type={
                    "name": "Cultural Entity",
                    "subtype": None,
                },
                information_to_collect=[
                    {
                        "name": "overview",
                        "priority": 5,
                    },
                    {
                        "name": "history",
                        "priority": 4,
                    },
                    {
                        "name": "cultural significance",
                        "priority": 4,
                    },
                ],
                reason=(
                    "Planner failed, so the entity was "
                    "retained to avoid losing coverage."
                ),
            )

        print(
            f"✓ Gemini finished "
            f"({time.time() - llm_start:.2f}s)"
        )

        entity.planner = decision

        planned_count += 1

        if decision.include:
            planned_entities.append(entity)
        else:
            rejected_entities.append(entity)

        print(
            f"Include: {decision.include}"
        )

        print(
            f"Expand: {decision.expand}"
        )

        print(
            f"Type: {decision.entity_type.name}"
        )

        if decision.entity_type.subtype:
            print(
                f"Subtype: {decision.entity_type.subtype}"
            )

        print("Information to collect:")

        for item in decision.information_to_collect:

            print(
                f"  - {item.name} "
                f"(priority {item.priority})"
            )

    print("\n" + "=" * 80)
    print(
        f"Planner finished in "
        f"{time.time() - total_start:.2f}s"
    )
    print(
        f"Successfully planned "
        f"{planned_count}/{len(entities)} entities."
    )
    print(
        f"Included {len(planned_entities)} entities; "
        f"excluded {len(rejected_entities)}."
    )
    print("=" * 80)

    planned_cache_path = save_entities_to_stage(
        seed,
        "planned",
        planned_entities,
    )
    rejected_cache_path = save_entities_to_stage(
        seed,
        "rejected",
        rejected_entities,
    )

    print(
        "Cached planner results to "
        f"{planned_cache_path} and {rejected_cache_path}."
    )

    return {
        "discovered_entities": planned_entities,
        "rejected_entities": rejected_entities,
    }
