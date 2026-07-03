from langgraph.graph import START, END, StateGraph

from src.graph.state import DiscoveryState

from src.nodes.wikipedia_discovery import wikipedia_discovery_node
from src.nodes.wikipedia_enricher import wikipedia_enricher_node
from src.planner.node import planner_node
from src.search.node import search_node
from src.fetcher.node import fetcher_node


def build_graph():

    graph = StateGraph(

        DiscoveryState

    )

    graph.add_node(

        "discover",

        wikipedia_discovery_node,

    )


    graph.add_node(
        "wikipedia_enricher",
        wikipedia_enricher_node,
        )

    graph.add_node(
        "planner",
        planner_node,
    )

    graph.add_node(
        "search",
        search_node,
    )

    graph.add_node(
        "fetch",
        fetcher_node,
    )

    graph.add_edge(

        START,

        "discover",

    )

    graph.add_edge(
        "discover",
        "wikipedia_enricher",
    )

    graph.add_edge(
        "wikipedia_enricher",
        "planner",
    )

    graph.add_edge(
        "planner",
        "search",
    )

    graph.add_edge(
        "search",
        "fetch",
    )

    graph.add_edge(
        "fetch",
        END,
    )

    return graph.compile()