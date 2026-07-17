import requests


def fetch_article(title: str):

    url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "redirects": 1,
        "titles": title,
    }

    headers = {
        "User-Agent": "QAResearchPipeline/1.0 (research project; contact: begum.atay0106@gmail.com)"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30
    )

    print("STATUS:", response.status_code)
    print("CONTENT TYPE:", response.headers.get("content-type"))
    print("FIRST 500 CHARS:")
    print(response.text[:500])

    response.raise_for_status()

    data = response.json()

    page = next(
        iter(
            data["query"]["pages"].values()
        )
    )

    return {
        "title": title,
        "text": page.get("extract", "")
    }

