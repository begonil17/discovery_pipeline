from langgraph.graph import StateGraph, START, END

from src.nugget_pipeline.graph.state import DataCollectionState

from src.nugget_pipeline.nodes.url_fetch_node import url_fetch_node
from src.nugget_pipeline.nodes.chunk_articles_node import chunk_articles_node
from src.nugget_pipeline.nodes.raw_qa_node import raw_qa_node
from src.nugget_pipeline.nodes.nugget_qa_node import nugget_qa_node


def route_after_chunking(state):

    if state.get("enable_raw_qa", False):
        return ["raw_qa", "nugget_qa"]

    return ["nugget_qa"]


def build_graph():

    graph = StateGraph(DataCollectionState)

    graph.add_node(
        "fetch_articles",
        url_fetch_node,
    )

    graph.add_node(
        "chunk_articles",
        chunk_articles_node,
    )

    graph.add_node(
        "raw_qa",
        raw_qa_node,
    )

    graph.add_node(
        "nugget_qa",
        nugget_qa_node,
    )

    graph.add_edge(
        START,
        "fetch_articles",
    )

    graph.add_edge(
        "fetch_articles",
        "chunk_articles",
    )

    graph.add_conditional_edges(
        "chunk_articles",
        route_after_chunking,
        {
            "raw_qa": "raw_qa",
            "nugget_qa": "nugget_qa",
        },
    )

    graph.add_edge(
        "raw_qa",
        END,
    )

    graph.add_edge(
        "nugget_qa",
        END,
    )

    return graph.compile()

