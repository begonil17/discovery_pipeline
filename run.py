import json
import re

from src.graph.workflow import build_graph

from src.schemas.seed import Seed

from src.config.settings import DISCOVERED_DIR

DISCOVERED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

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


def build_output_filename(
    title: str,
    depth: int,
) -> str:

    safe_title = re.sub(
        r'[<>:"/\\|?*]',
        "",
        title,
    )

    safe_title = re.sub(
        r"\s+",
        "_",
        safe_title.strip(),
    )

    return f"{safe_title}_depth_{depth}.json"

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

                    entity_limit=300,

                )

            }

        )

        entities = [

            entity.model_dump()

            for entity in result["discovered_entities"]

        ]

        output_path = (
            DISCOVERED_DIR
            / build_output_filename(
                title,
                depth,
            )
        )

        with open(

            output_path,

            "w",

            encoding="utf-8",

        ) as f:

            json.dump(

                entities,

                f,

                ensure_ascii=False,

                indent=2,

            )

        print(

            f"Discovered {len(entities)} entities. "
            f"Saved to {output_path}."

        )

    except Exception as e:

        print(
            f"Failed to process: {title} "
            f"(depth={depth})"
        )

        print(e)
        print("Continuing with the next seed.")
