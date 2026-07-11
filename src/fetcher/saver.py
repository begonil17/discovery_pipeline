import json
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse

OUTPUT_DIR = Path("data/raw_documents")


def sanitize_filename(name: str) -> str:

    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip()

    return name


def document_filename(document) -> str:

    source = sanitize_filename(document.source) or "source"

    parsed = urlparse(document.url)

    url_hint = " ".join(
        part
        for part in (
            parsed.path.strip("/"),
            parsed.query,
        )
        if part
    )

    if not url_hint:
        url_hint = document.title or "index"

    url_hint = re.sub(
        r"[^0-9A-Za-z._-]+",
        "_",
        url_hint,
    ).strip("._-")

    if not url_hint:
        url_hint = "document"

    url_hint = url_hint[:80]

    digest = hashlib.sha1(
        document.url.encode("utf-8"),
    ).hexdigest()[:10]

    return f"{source}__{url_hint}__{digest}.json"


def existing_document_urls(entity) -> set[str]:

    entity_dir = OUTPUT_DIR / sanitize_filename(entity.title)

    if not entity_dir.is_dir():
        return set()

    urls = set()

    for path in entity_dir.glob("*.json"):

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)

        except (OSError, json.JSONDecodeError):
            continue

        url = data.get("url")

        if isinstance(url, str) and url.strip():
            urls.add(url.strip())

    return urls


def save_documents(entity):

    entity_dir = OUTPUT_DIR / sanitize_filename(entity.title)

    entity_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for document in entity.documents:

        filename = document_filename(document)

        output_path = entity_dir / filename

        data = {
            "url": document.url,
            "source": document.source,
            "title": document.title,
            "text": document.text,
        }

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4,
            )
