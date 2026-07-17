from langgraph.graph import StateGraph, START, END

from src.nugget_pipeline.graph.state import DataCollectionState
from src.nugget_pipeline.nodes.topic_selection import topic_selection_node
from src.nugget_pipeline.nodes.wikipedia_fetch_node import wikipedia_fetch_node
from src.nugget_pipeline.nodes.chunk_articles_node import chunk_articles_node
from src.nugget_pipeline.nodes.raw_qa_node import raw_qa_node
from src.nugget_pipeline.nodes.nugget_qa_node import nugget_qa_node


    # parallel test branches
def route_after_chunking(state):
    if state.get("enable_raw_qa", False):
        return ["raw_qa", "nugget_qa"]

    return ["nugget_qa"]

def build_graph():
    graph = StateGraph(DataCollectionState)

    graph.add_node("select_topics", topic_selection_node)
    graph.add_node("fetch_wikipedia", wikipedia_fetch_node)
    graph.add_node("chunk_articles", chunk_articles_node)
    graph.add_node("raw_qa", raw_qa_node)
    graph.add_node("nugget_qa", nugget_qa_node)

    graph.add_edge(START, "select_topics")
    graph.add_edge("select_topics", "fetch_wikipedia")
    graph.add_edge("fetch_wikipedia", "chunk_articles")

    graph.add_conditional_edges(
        "chunk_articles",
        route_after_chunking,
        {
            "raw_qa": "raw_qa",
            "nugget_qa": "nugget_qa",
        },
    )

    graph.add_edge("raw_qa", END)
    graph.add_edge("nugget_qa", END)

    return graph.compile()

