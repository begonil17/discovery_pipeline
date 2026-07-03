from src.wikipedia.client import WikipediaClient

from src.wikipedia.bfs import WikipediaBFS


def wikipedia_discovery_node(state):

    client = WikipediaClient(

        state["seed"].language

    )

    bfs = WikipediaBFS(client)
    
    print("Starting Wikipedia discovery...")
    entities = bfs.discover(

        state["seed"]

    )
    print(f"Discovered {len(entities)} entities.")
    
    return {

        "discovered_entities": entities,

        "errors": [],

    }