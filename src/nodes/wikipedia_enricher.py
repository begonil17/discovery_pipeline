from src.config.settings import WIKIPEDIA_BATCH_SIZE
from src.discovery.cache import (
    load_entities_from_stage,
    save_entities_to_stage,
)
from src.wikipedia.client import WikipediaClient


def batch(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def wikipedia_enricher_node(state):
    seed = state["seed"]

    if not state.get("refresh_enrichment", False):
        cached_entities = load_entities_from_stage(
            seed,
            "enriched",
        )

        if cached_entities is not None:
            print(
                "Loaded enriched entities from cache "
                f"({len(cached_entities)} entities)."
            )
            return {
                "discovered_entities": cached_entities
            }

    client = WikipediaClient(
        seed.language
    )

    entities = state["discovered_entities"]

    for entity_batch in batch(entities, WIKIPEDIA_BATCH_SIZE):
        titles = [
            entity.title
            for entity in entity_batch
        ]

        page_info = client.get_pages_info(
            titles
        )

        for entity in entity_batch:
            info = page_info.get(entity.title)

            if info is None:
                continue

            entity.summary = info["summary"]
            entity.categories = info["categories"]
            print(f"  enriched {entity.title}")

    cache_path = save_entities_to_stage(
        seed,
        "enriched",
        entities,
    )

    print(
        "Cached enriched entities to "
        f"{cache_path}."
    )

    return {
        "discovered_entities": entities
    }
