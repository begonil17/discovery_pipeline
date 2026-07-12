from src.graph.workflow import build_graph
from src.schemas.seed import Seed
from src.source_first.config import SourceFirstConfig


seeds = [
    "Türkiyede popüler kültür",
    "Türkiyede sinema & televizyon",
    "Dünyada sinema & televizyon",
]


app = build_graph()
config = SourceFirstConfig()
fetching_config = config.fetching_config()
max_documents_per_run = fetching_config.get(
    "max_documents_per_run",
)

if isinstance(max_documents_per_run, int):
    max_documents_per_run = max(1, max_documents_per_run)
else:
    max_documents_per_run = None

seed_count = len(seeds)
remaining_document_budget = max_documents_per_run

for seed_index, title in enumerate(
    seeds,
    start=1,
):
    print(
        f"Running source-first graph for: {title}"
    )

    document_budget = None

    if remaining_document_budget is not None:
        if remaining_document_budget <= 0:
            print(
                "Run document budget exhausted; "
                "skipping remaining seeds."
            )
            break

        remaining_seed_count = seed_count - seed_index + 1
        document_budget = (
            remaining_document_budget + remaining_seed_count - 1
        ) // remaining_seed_count

        print(
            "Document budget for seed: "
            f"{document_budget}/{remaining_document_budget} remaining "
            f"({max_documents_per_run} run cap)"
        )

    try:
        result = app.invoke(
            {
                "seed": Seed(
                    title=title,
                    max_depth=0,
                    entity_limit=0,
                ),
                "document_budget": document_budget,
                "run_document_budget": max_documents_per_run,
                "run_seed_count": seed_count,
                "run_seed_index": seed_index,
            }
        )
        fetched_count = len(result.get("documents", []))

        if remaining_document_budget is not None:
            remaining_document_budget = max(
                0,
                remaining_document_budget - fetched_count,
            )

        print(
            "Pipeline finished for "
            f"{title}: "
            f"{len(result.get('candidates', []))} candidates, "
            f"{len(result.get('selected_candidates', []))} selected, "
            f"{fetched_count} fetched."
        )

        if result.get("errors"):
            print("Errors:")
            for error in result["errors"]:
                print(f"- {error}")

    except Exception as e:
        print(f"Failed to process: {title}")
        print(e)
        print("Continuing with the next seed.")
