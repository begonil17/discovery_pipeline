import json
from src.nugget_pipeline.config import DATA_DIR
from src.nugget_pipeline.wikipedia.url_fetcher import fetch_article_from_url

RAW_DIR = DATA_DIR / "raw_url_articles"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(title: str) -> str:
    return (
        title
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def url_fetch_node(state):

    paths = []

    errors = state.get("errors", [])

    urls = state["article_urls"]

    for url in urls:

        try:

            article = fetch_article_from_url(url)

            output_path = RAW_DIR / f"{safe_filename(article['title'])}.json"

            if output_path.exists():

                paths.append(str(output_path))
                continue

            output_path.write_text(
                json.dumps(
                    article,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            paths.append(str(output_path))

            print(f"âœ“ {article['title']}")

        except Exception as e:

            print(f"âœ— Failed: {url}")
            print(f"  {e}")

            errors.append(
                f"{url}: {e}"
            )

            # Continue with the next URL
            continue

    print(f"\nFinished fetching {len(paths)} articles.")

    return {
        "raw_article_paths": paths,
        "errors": errors,
    }


