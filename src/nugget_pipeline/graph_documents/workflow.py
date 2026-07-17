from langgraph.graph import END, START, StateGraph

from src.nugget_pipeline.graph.state import DataCollectionState
from src.nugget_pipeline.nodes.chunk_raw_documents_node import chunk_raw_documents_node
from src.nugget_pipeline.nodes.nugget_qa_node import nugget_qa_node


def build_graph():
    graph = StateGraph(DataCollectionState)

    graph.add_node("chunk_raw_documents", chunk_raw_documents_node)
    graph.add_node("nugget_qa", nugget_qa_node)

    graph.add_edge(START, "chunk_raw_documents")
    graph.add_edge("chunk_raw_documents", "nugget_qa")
    graph.add_edge("nugget_qa", END)

    return graph.compile()


