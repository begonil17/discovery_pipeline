from langgraph.graph import END, START, StateGraph

from src.source_first.nodes import (
    candidate_listing_node,
    fetcher_node,
    scoring_node,
    source_registry_node,
    topic_planner_node,
)
from src.source_first.state import SourceFirstState


def build_source_first_graph():
    graph = StateGraph(SourceFirstState)

    graph.add_node(
        "topic_planner",
        topic_planner_node,
    )
    graph.add_node(
        "source_registry",
        source_registry_node,
    )
    graph.add_node(
        "candidate_listing",
        candidate_listing_node,
    )
    graph.add_node(
        "scoring",
        scoring_node,
    )
    graph.add_node(
        "fetch",
        fetcher_node,
    )

    graph.add_edge(
        START,
        "topic_planner",
    )
    graph.add_edge(
        "topic_planner",
        "source_registry",
    )
    graph.add_edge(
        "source_registry",
        "candidate_listing",
    )
    graph.add_edge(
        "candidate_listing",
        "scoring",
    )
    graph.add_edge(
        "scoring",
        "fetch",
    )
    graph.add_edge(
        "fetch",
        END,
    )

    return graph.compile()
