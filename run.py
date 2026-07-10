from src.graph.workflow import build_graph
from src.schemas.seed import Seed


seeds = [
    "Türk mutfağı",
    "Türkiye'de futbol",
    "Türkiye'de eğitim",
    "Türkiye'de voleybol",
    "Dünyada futbol",
    "Dünya mutfağı",
    "Türk tarihi",
]


app = build_graph()

for title in seeds:
    print(
        f"Running source-first graph for: {title}"
    )

    try:
        result = app.invoke(
            {
                "seed": Seed(
                    title=title,
                    max_depth=0,
                    entity_limit=0,
                )
            }
        )

        print(
            "Pipeline finished for "
            f"{title}: "
            f"{len(result.get('candidates', []))} candidates, "
            f"{len(result.get('selected_candidates', []))} selected, "
            f"{len(result.get('documents', []))} fetched."
        )

        if result.get("errors"):
            print("Errors:")
            for error in result["errors"]:
                print(f"- {error}")

    except Exception as e:
        print(f"Failed to process: {title}")
        print(e)
        print("Continuing with the next seed.")
