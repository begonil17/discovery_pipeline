from src.fetcher.client import FetcherClient
from src.fetcher.saver import (
    existing_document_urls,
    save_documents,
)


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

        if entity.search_plan is None:

            print("No search plan.")

            entity.documents = []

            continue

        print("-" * 50)
        print("Fetching entity:")
        print(entity.title)
        print("-" * 50)

        documents = []
        searched_urls = set()
        document_urls = set()
        saved_urls = existing_document_urls(entity)

        for task in entity.search_plan.tasks:

            print(
                f"\nInformation: {task.information}"
            )

            for result in task.results:

                url = result.url.strip()

                if not url:
                    continue

                if url in searched_urls:

                    print(
                        "Skipping duplicate search result: "
                        f"{url}"
                    )

                    continue

                searched_urls.add(url)

                if url in saved_urls:

                    print(
                        "Skipping already saved URL: "
                        f"{url}"
                    )

                    continue

                print(
                    f"Fetching: {url}"
                )

                fetched_documents = client.fetch_many(
                    url
                )

                if not fetched_documents:

                    continue

                for document in fetched_documents:

                    document_url = document.url.strip()

                    if not document_url:
                        continue

                    if (
                        document_url in document_urls
                        or document_url in saved_urls
                    ):

                        print(
                            "Skipping duplicate fetched document: "
                            f"{document_url}"
                        )

                        continue

                    document_urls.add(document_url)
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
