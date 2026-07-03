import time

from src.planner.prompt import build_prompt
from src.planner.registry import Registry
from src.planner.schemas import PlannerDecision
from src.config.settings import PLANNER_MODEL
from src.llm.client import LLMClient


def planner_node(state):

    print("\n" + "=" * 80)
    print("Starting Knowledge Planner")
    print("=" * 80)

    registry = Registry()

    client = LLMClient()

    seed = state["seed"]

    entities = state["discovered_entities"]

    print(f"Planning {len(entities)} entities...\n")

    planned_entities = []

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
            continue

        print(
            f"✓ Gemini finished "
            f"({time.time() - llm_start:.2f}s)"
        )

        entity.planner = decision

        planned_entities.append(entity)

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
        f"{len(planned_entities)}/{len(entities)} entities."
    )
    print("=" * 80)

    return {
        "discovered_entities": planned_entities,
    }