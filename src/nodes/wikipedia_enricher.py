from src.wikipedia.client import WikipediaClient
from src.config.settings import WIKIPEDIA_BATCH_SIZE


def batch(items, size):

    for i in range(0, len(items), size):

        yield items[i:i + size]


def wikipedia_enricher_node(state):

    client = WikipediaClient(
        state["seed"].language
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
        print(f"  ✓ {entity.title}")
    return {

        "discovered_entities": entities

    }