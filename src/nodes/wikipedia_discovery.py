import json
import re

from src.config.settings import DISCOVERED_DIR
from src.wikipedia.client import WikipediaClient

from src.wikipedia.bfs import WikipediaBFS


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


def save_discovered_entities(
    seed,
    entities,
):

    DISCOVERED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        DISCOVERED_DIR
        / build_output_filename(
            seed.title,
            seed.max_depth,
        )
    )

    data = [
        entity.model_dump()
        for entity in entities
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def wikipedia_discovery_node(state):

    seed = state["seed"]

    client = WikipediaClient(

        seed.language

    )

    bfs = WikipediaBFS(client)
    
    print("Starting Wikipedia discovery...")
    entities = bfs.discover(

        seed

    )
    print(f"Discovered {len(entities)} entities.")

    output_path = save_discovered_entities(
        seed,
        entities,
    )

    print(
        "Saved discovered entities to "
        f"{output_path}."
    )
    
    return {

        "discovered_entities": entities,

        "errors": [],

    }
