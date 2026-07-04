from src.graph.workflow import build_graph

from src.schemas.seed import Seed

seeds = {
    "Türk mutfağı": 2,
    "Türk kültürü": 4,
    "Türkiye'de turizm": 2,
    "Türk folkloru": 2,
    "Türkiye'de eğitim": 1,
    "Türkiye'de spor": 2,
    "Türk müziği": 2,
    "Türk edebiyatı": 2,
    "Türkiye'de mimarlık": 1,
    "Türkiye'nin illeri": 2,
}


app = build_graph()

for title, depth in seeds.items():

    print(
        f"Running graph for: {title} "
        f"(depth={depth})"
    )

    try:

        result = app.invoke(

            {

                "seed": Seed(

                    title=title,

                    max_depth=depth,

                    entity_limit=250,

                )

            }

        )

        print(

            "Pipeline finished for "
            f"{title} with "
            f"{len(result['discovered_entities'])} "
            "entities."

        )

    except Exception as e:

        print(
            f"Failed to process: {title} "
            f"(depth={depth})"
        )

        print(e)
        print("Continuing with the next seed.")
