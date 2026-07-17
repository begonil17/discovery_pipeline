import json
from pathlib import Path

from src.nugget_pipeline.chunker import chunk_text
from src.nugget_pipeline.cleaner import clean_article


def chunk_articles_node(state):
    article_chunks = {}

    for path_str in state["raw_article_paths"]:
        path = Path(path_str)
        article = json.loads(path.read_text(encoding="utf-8"))

        title = article["title"]
        text = clean_article(article["text"])

        chunks = chunk_text(text)

        max_chunks = state.get("max_chunks_per_article")
        if max_chunks:
            chunks = chunks[:max_chunks]

        article_chunks[title] = chunks

    print(f"Finished article chunking. Chunked {len(article_chunks)} articles.")

    return {"article_chunks": article_chunks}

