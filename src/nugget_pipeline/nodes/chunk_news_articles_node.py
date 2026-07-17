import json
from pathlib import Path

from src.nugget_pipeline.chunker import chunk_text
from src.nugget_pipeline.cleaner import clean_article
from src.nugget_pipeline.config import DATA_DIR


NEWS_ARTICLES_DIR = DATA_DIR / "news_articles"


def positive_limit(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def chunk_news_articles_node(state):
    root = Path(state.get("news_articles_dir") or NEWS_ARTICLES_DIR)
    errors = list(state.get("errors", []))
    article_chunks = {}
    article_titles = {}
    output_filename_stems = {}

    if not root.is_dir():
        message = f"News articles directory does not exist: {root}"
        print(message)
        errors.append(message)
        return {
            "article_chunks": article_chunks,
            "article_titles": article_titles,
            "output_filename_stems": output_filename_stems,
            "errors": errors,
        }

    article_paths = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() == ".json"
        ),
        key=lambda path: path.name.casefold(),
    )

    max_articles = positive_limit(state.get("max_articles"))
    if max_articles:
        article_paths = article_paths[:max_articles]

    max_chunks = positive_limit(state.get("max_chunks_per_article"))

    for article_path in article_paths:
        try:
            article = json.loads(article_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            message = f"Failed to read {article_path}: {exc}"
            print(message)
            errors.append(message)
            continue

        title = article.get("title") if isinstance(article, dict) else None
        text = article.get("text") if isinstance(article, dict) else None

        if not isinstance(title, str) or not title.strip():
            message = f"Skipped news article with empty or missing title: {article_path}"
            print(message)
            errors.append(message)
            continue

        if not isinstance(text, str) or not text.strip():
            message = f"Skipped news article with empty or missing text: {article_path}"
            print(message)
            errors.append(message)
            continue

        chunks = chunk_text(clean_article(text))
        if max_chunks:
            chunks = chunks[:max_chunks]

        if not chunks:
            message = f"No usable text found in news article: {article_path}"
            print(message)
            errors.append(message)
            continue

        article_key = article_path.stem
        article_chunks[article_key] = chunks
        article_titles[article_key] = title.strip()
        output_filename_stems[article_key] = article_path.stem

        print(
            f"Chunked news article {title.strip()}: {len(chunks)} chunks."
        )

    print(
        f"Finished news article chunking. "
        f"Chunked {len(article_chunks)} articles."
    )

    return {
        "article_chunks": article_chunks,
        "article_titles": article_titles,
        "output_filename_stems": output_filename_stems,
        "errors": errors,
    }


