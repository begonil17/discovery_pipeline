import json
from pathlib import Path

from src.config.settings import DATA_DIR, DISCOVERY_MANIFEST_PATH
from src.fetcher.saver import (
    document_id,
    entity_directory,
    save_document,
)
from src.fetcher.schemas import Document
from src.persistence.manifest import (
    atomic_write_json,
    load_json,
    relative_path,
    utc_now_iso,
)


FetcherClient = None


def build_fetcher_client():
    global FetcherClient

    if FetcherClient is None:
        from src.fetcher.client import FetcherClient as ImportedFetcherClient

        FetcherClient = ImportedFetcherClient

    return FetcherClient()


def empty_discovery_manifest() -> dict:
    return {
        "version": 1,
        "entities": {},
    }


def load_discovery_manifest() -> dict:
    manifest = load_json(
        DISCOVERY_MANIFEST_PATH,
        empty_discovery_manifest(),
    )

    if not isinstance(manifest, dict):
        manifest = empty_discovery_manifest()

    manifest.setdefault("version", 1)
    manifest.setdefault("entities", {})
    return manifest


def save_discovery_manifest(manifest: dict) -> None:
    manifest["updated_at"] = utc_now_iso()
    atomic_write_json(DISCOVERY_MANIFEST_PATH, manifest)


def entity_record(manifest: dict, entity) -> dict:
    entities = manifest.setdefault("entities", {})
    record = entities.setdefault(
        entity.title,
        {
            "title": entity.title,
            "documents": {},
            "legacy_documents": [],
            "fetch_attempts": {},
        },
    )
    record.setdefault("title", entity.title)
    record.setdefault("documents", {})
    record.setdefault("legacy_documents", [])
    record.setdefault("fetch_attempts", {})
    return record


def manifest_document_record(manifest: dict, entity, url: str) -> dict | None:
    record = entity_record(manifest, entity)
    document_record = record.get("documents", {}).get(document_id(url))
    return document_record if isinstance(document_record, dict) else None


def path_from_manifest(record: dict) -> Path | None:
    path_value = record.get("path")

    if not isinstance(path_value, str) or not path_value:
        return None

    path = Path(path_value)

    if path.is_absolute():
        return path

    return DATA_DIR / path


def load_document_from_path(path: Path) -> Document | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        return None

    return Document(
        url=data.get("url") or "",
        source=data.get("source") or path.stem,
        title=data.get("title") or path.stem,
        text=text,
    )


def load_manifest_document(manifest: dict, entity, url: str) -> Document | None:
    record = manifest_document_record(manifest, entity, url)

    if not record or record.get("status") != "fetched":
        return None

    path = path_from_manifest(record)

    if path is None or not path.exists():
        return None

    return load_document_from_path(path)


def find_existing_document_for_url(entity, url: str) -> tuple[Document, Path] | None:
    directory = entity_directory(entity)

    if not directory.is_dir():
        return None

    for path in sorted(directory.glob("*.json")):
        document = load_document_from_path(path)

        if document is not None and document.url == url:
            return document, path

    return None


def legacy_document_paths(entity) -> list[Path]:
    directory = entity_directory(entity)

    if not directory.is_dir():
        return []

    paths = []

    for path in sorted(directory.glob("*.json")):
        document = load_document_from_path(path)

        if document is not None and not document.url:
            paths.append(path)

    return paths


def load_legacy_documents(entity) -> list[Document]:
    documents = []

    for path in legacy_document_paths(entity):
        document = load_document_from_path(path)

        if document is not None:
            documents.append(document)

    return documents


def record_existing_document(
    manifest: dict,
    entity,
    document: Document,
    path: Path,
) -> None:
    record = entity_record(manifest, entity)
    key = document_id(document.url)
    record["documents"][key] = {
        "document_id": key,
        "url": document.url,
        "source": document.source,
        "title": document.title,
        "path": relative_path(path, DATA_DIR),
        "status": "fetched",
        "updated_at": utc_now_iso(),
    }
    record["updated_at"] = utc_now_iso()


def record_fetched_document(
    manifest: dict,
    entity,
    document: Document,
    path: Path,
) -> None:
    record_existing_document(
        manifest,
        entity,
        document,
        path,
    )
    entity_record(manifest, entity)["last_fetch_status"] = "fetched"


def record_fetch_failure(
    manifest: dict,
    entity,
    url: str,
    error: str,
) -> None:
    record = entity_record(manifest, entity)
    key = document_id(url)
    record["fetch_attempts"][key] = {
        "document_id": key,
        "url": url,
        "status": "failed",
        "error": error,
        "updated_at": utc_now_iso(),
    }
    record["last_fetch_status"] = "failed"
    record["updated_at"] = utc_now_iso()


def record_legacy_documents(
    manifest: dict,
    entity,
    paths: list[Path],
) -> None:
    record = entity_record(manifest, entity)
    seen = {
        item.get("path")
        for item in record.get("legacy_documents", [])
        if isinstance(item, dict)
    }

    for path in paths:
        relative = relative_path(path, DATA_DIR)

        if relative in seen:
            continue

        record["legacy_documents"].append(
            {
                "path": relative,
                "status": "legacy_without_url",
                "updated_at": utc_now_iso(),
            }
        )
        seen.add(relative)

    record["last_fetch_status"] = "legacy_cached"
    record["updated_at"] = utc_now_iso()


def planned_urls(entity) -> list[str]:
    if entity.search_plan is None:
        return []

    urls = []
    seen = set()

    for task in entity.search_plan.tasks:
        for result in task.results:
            if result.url in seen:
                continue

            urls.append(result.url)
            seen.add(result.url)

    return urls


def fetcher_node(state):
    print("\n" + "=" * 80)
    print("Starting Fetcher")
    print("=" * 80)

    client = build_fetcher_client()
    manifest = load_discovery_manifest()
    force_fetch = state.get("refresh_fetch", False)

    entities = state["discovered_entities"]

    for entity_no, entity in enumerate(entities, start=1):
        print(
            f"\n[{entity_no}/{len(entities)}] {entity.title}"
        )

        urls = planned_urls(entity)

        if not urls:
            print("No search plan.")
            entity.documents = load_legacy_documents(entity)
            continue

        legacy_paths = legacy_document_paths(entity)
        has_manifest_documents = bool(
            entity_record(manifest, entity).get("documents")
        )

        if legacy_paths and not has_manifest_documents and not force_fetch:
            documents = load_legacy_documents(entity)
            record_legacy_documents(
                manifest,
                entity,
                legacy_paths,
            )
            save_discovery_manifest(manifest)
            entity.documents = documents
            print("-" * 50)
            print(
                "Using legacy raw documents without URL metadata; "
                "set refresh_fetch=True to rebuild URL-tracked files."
            )
            print(entity.title)
            print("-" * 50)
            continue

        print("-" * 50)
        print("Fetching entity:")
        print(entity.title)
        print("-" * 50)

        documents = []

        for url in urls:
            cached_document = None

            if not force_fetch:
                cached_document = load_manifest_document(
                    manifest,
                    entity,
                    url,
                )

                if cached_document is None:
                    existing = find_existing_document_for_url(
                        entity,
                        url,
                    )

                    if existing is not None:
                        cached_document, existing_path = existing
                        record_existing_document(
                            manifest,
                            entity,
                            cached_document,
                            existing_path,
                        )
                        save_discovery_manifest(manifest)

            if cached_document is not None:
                documents.append(cached_document)
                print(f"Skipping already fetched URL: {url}")
                continue

            print(f"Fetching: {url}")

            try:
                document = client.fetch(url)
            except Exception as exc:
                error = str(exc)
                record_fetch_failure(
                    manifest,
                    entity,
                    url,
                    error,
                )
                save_discovery_manifest(manifest)
                print(f"Failed to fetch {url}: {error}")
                continue

            if document is None:
                record_fetch_failure(
                    manifest,
                    entity,
                    url,
                    "Fetcher returned no document.",
                )
                save_discovery_manifest(manifest)
                continue

            path = save_document(entity, document)
            record_fetched_document(
                manifest,
                entity,
                document,
                path,
            )
            save_discovery_manifest(manifest)
            documents.append(document)

        entity.documents = documents

        print(
            f"Available documents for entity: {len(documents)}."
        )

    print("\nFetcher finished.")

    return {
        "discovered_entities": entities,
    }
