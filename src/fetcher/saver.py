import hashlib
import json
import re
from pathlib import Path

from src.config.settings import RAW_DOCUMENTS_DIR


OUTPUT_DIR = RAW_DOCUMENTS_DIR


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip()
    return name or "untitled"


def document_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def entity_directory(entity) -> Path:
    return OUTPUT_DIR / sanitize_filename(entity.title)


def document_path(entity, document) -> Path:
    source = sanitize_filename(document.source)
    return entity_directory(entity) / f"{source}-{document_id(document.url)}.json"


def save_document(entity, document) -> Path:
    output_path = document_path(entity, document)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "url": document.url,
        "source": document.source,
        "title": document.title,
        "text": document.text,
    }

    temporary_path = output_path.with_name(f"{output_path.name}.tmp")
    temporary_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path


def save_documents(entity):
    paths = []

    for document in entity.documents:
        paths.append(save_document(entity, document))

    return paths
