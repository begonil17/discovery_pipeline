import json
import re
from pathlib import Path

OUTPUT_DIR = Path("data/raw_documents")


def sanitize_filename(name: str) -> str:

    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip()

    return name


def save_documents(entity):

    entity_dir = OUTPUT_DIR / sanitize_filename(entity.title)

    entity_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for document in entity.documents:

        filename = sanitize_filename(document.source) + ".json"

        output_path = entity_dir / filename

        data = {
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