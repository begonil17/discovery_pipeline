import json
from src.nugget_pipeline.config import DATA_DIR
from src.nugget_pipeline.wikipedia.fetcher import fetch_article

RAW_DIR = DATA_DIR / "raw_articles"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def safe_filename(title: str) -> str:
    return (
        title
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

def wikipedia_fetch_node(state):
    paths = []
    errors = state.get("errors", [])

    topics = state["topics"]

    max_articles = state.get("max_articles")
    if max_articles:
        topics = topics[:max_articles]

    for title in topics:
        try:
            output_path = RAW_DIR / f"{safe_filename(title)}.json"

            if output_path.exists():
                paths.append(str(output_path))
                continue

            article = fetch_article(title)

            output_path.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            paths.append(str(output_path))

        except Exception as e:
            errors.append(f"Failed to fetch {title}: {e}")

    print(f"Finished Wikipedia article fetch. Saved {len(paths)} articles.")

    return {
        "raw_article_paths": paths,
        "errors": errors,
    }



