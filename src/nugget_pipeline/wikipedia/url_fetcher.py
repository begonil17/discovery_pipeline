import requests
from urllib.parse import unquote, urlparse

HEADERS = {
    "User-Agent": "QAResearchPipeline/1.0 (research project; contact: begum.atay0106@gmail.com)"
}


def fetch_article_from_url(url: str):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    article_title = unquote(url.rsplit("/", 1)[-1])

    parsed = urlparse(url)
    api_url = f"{parsed.scheme}://{parsed.netloc}/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "redirects": 1,
        "titles": article_title,
    }

    api_response = requests.get(
        api_url,
        params=params,
        headers=HEADERS,
        timeout=30,
    )

    print("STATUS:", api_response.status_code)
    print("CONTENT TYPE:", api_response.headers.get("content-type"))
    print("FIRST 500 CHARS:")
    print(api_response.text[:500])

    api_response.raise_for_status()

    data = api_response.json()

    page = next(iter(data["query"]["pages"].values()))

    if "missing" in page:
        raise ValueError(f"Wikipedia article does not exist: {url}")

    text = page.get("extract", "").strip()

    if not text:
        raise ValueError(f"Article is empty: {url}")

    return {
        "title": page["title"],
        "text": page.get("extract", ""),
    }

