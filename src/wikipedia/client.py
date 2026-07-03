import requests
from urllib.parse import quote

from src.config.settings import (
    USER_AGENT,
    REQUEST_TIMEOUT,
)

class WikipediaClient:

    def __init__(self, language="tr"):

        self.language = language

        self.base_url = (
            f"https://{language}.wikipedia.org/w/api.php"
        )

        self.headers = {
            "User-Agent": USER_AGENT
        }

    def get_links(self, title):

        links = []

        params = {

            "action": "query",

            "format": "json",

            "prop": "links",

            "titles": title,

            "pllimit": "max",

            "redirects": 1,

        }

        while True:

            response = requests.get(

                self.base_url,

                params=params,

                headers=self.headers,

                timeout=REQUEST_TIMEOUT,

            )

            response.raise_for_status()

            data = response.json()

            pages = data["query"]["pages"]

            page = next(iter(pages.values()))

            links.extend(page.get("links", []))

            if "continue" not in data:

                break

            params.update(data["continue"])

        return links
    
    def get_pages_info(self, titles: list[str]):

        if not titles:
            return {}

        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts|categories",
            "titles": "|".join(titles),
            "redirects": 1,
            "exintro": True,
            "explaintext": True,
            "cllimit": "max",
        }

        response = requests.get(
            self.base_url,
            params=params,
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        pages = response.json()["query"]["pages"]

        result = {}

        for page in pages.values():

            title = page.get("title")

            if not title:
                continue

            result[title] = {
                "summary": page.get("extract", ""),
                "categories": [
                    c["title"]
                    for c in page.get("categories", [])
                ],
            }

        return result
    
    def get_url(self, title):

        return (

            f"https://"

            f"{self.language}.wikipedia.org/wiki/"

            f"{quote(title.replace(' ', '_'))}"

        )
