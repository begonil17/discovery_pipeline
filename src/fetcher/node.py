from src.fetcher.client import FetcherClient
from src.fetcher.saver import save_documents

def fetcher_node(state):

    print("\n" + "=" * 80)
    print("Starting Fetcher")
    print("=" * 80)

    client = FetcherClient()

    entities = state["discovered_entities"]

    for entity_no, entity in enumerate(entities, start=1):

        print(
            f"\n[{entity_no}/{len(entities)}] {entity.title}"
        )

        documents = []

        if entity.search_plan is None:

            print("No search plan.")

            entity.documents = []

            continue

        for task in entity.search_plan.tasks:

            print(
                f"\nInformation: {task.information}"
            )

            for result in task.results:

                print(
                    f"Fetching: {result.url}"
                )

                document = client.fetch(
                    result.url
                )

                if document is None:

                    continue

                documents.append(document)

        entity.documents = documents
        save_documents(entity)

        print(
            f"Downloaded {len(documents)} documents."
        )

    print("\nFetcher finished.")

    return {

        "discovered_entities": entities,

    }