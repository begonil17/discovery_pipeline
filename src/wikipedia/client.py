import time
from urllib.parse import quote

import requests


MAX_RETRIES = 5
REQUEST_TIMEOUT = 90
REQUEST_DELAY = 0.25
INITIAL_BACKOFF = 5
USER_AGENT = (
    "DiscoveryPipelineBot/1.0 "
    "(Educational research project; "
    "contact: begum.atay0106@gmail.com)"
)


class WikipediaClient:

    def __init__(self, language="tr"):

        self.language = language

        self.base_url = (
            f"https://{language}.wikipedia.org/w/api.php"
        )

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
            }
        )

    def _request(
        self,
        params: dict,
    ):

        for retry_number in range(MAX_RETRIES + 1):

            try:

                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )

                if response.status_code == 429:

                    if retry_number == MAX_RETRIES:
                        response.raise_for_status()

                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    try:
                        wait = float(retry_after)
                    except (TypeError, ValueError):
                        wait = (
                            INITIAL_BACKOFF
                            * (2 ** retry_number)
                        )

                    print("Rate limited by Wikipedia.")
                    print(
                        f"Waiting {wait:g} seconds..."
                    )

                    time.sleep(wait)
                    continue

                response.raise_for_status()

                time.sleep(REQUEST_DELAY)

                return response

            except (
                requests.Timeout,
                requests.ConnectionError,
            ) as e:

                if retry_number == MAX_RETRIES:
                    raise

                wait = (
                    INITIAL_BACKOFF
                    * (2 ** retry_number)
                )

                print("Wikipedia request failed:")
                print(e)
                print(f"Waiting {wait} seconds...")

                time.sleep(wait)

        raise RuntimeError(
            "Wikipedia request retries exhausted."
        )

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

            response = self._request(params)

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

        response = self._request(params)

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
