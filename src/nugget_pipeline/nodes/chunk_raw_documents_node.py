import json
from pathlib import Path

from src.nugget_pipeline.chunker import chunk_text
from src.nugget_pipeline.cleaner import clean_article
from src.nugget_pipeline.config import RAW_DOCUMENTS_DIR


def positive_limit(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def chunk_raw_documents_node(state):
    root = Path(state.get("raw_documents_dir") or RAW_DOCUMENTS_DIR)
    errors = list(state.get("errors", []))
    article_chunks = {}
    output_filename_stems = {}
    source_document_paths = {}

    if not root.is_dir():
        message = f"Raw documents directory does not exist: {root}"
        print(message)
        errors.append(message)
        return {
            "article_chunks": article_chunks,
            "output_filename_stems": output_filename_stems,
            "source_document_paths": source_document_paths,
            "errors": errors,
        }

    entity_directories = sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    )

    max_entities = positive_limit(state.get("max_entities"))
    if max_entities:
        entity_directories = entity_directories[:max_entities]

    max_documents = positive_limit(state.get("max_documents_per_entity"))
    max_chunks = positive_limit(state.get("max_chunks_per_article"))
    processed_documents = 0

    for entity_directory in entity_directories:
        document_paths = sorted(
            (
                path
                for path in entity_directory.iterdir()
                if path.is_file() and path.suffix.lower() == ".json"
            ),
            key=lambda path: path.name.casefold(),
        )

        if max_documents:
            document_paths = document_paths[:max_documents]

        chunks = []
        usable_document_paths = []

        for document_path in document_paths:
            if max_chunks and len(chunks) >= max_chunks:
                break

            try:
                document = json.loads(document_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                message = f"Failed to read {document_path}: {exc}"
                print(message)
                errors.append(message)
                continue

            text = document.get("text") if isinstance(document, dict) else None
            if not isinstance(text, str) or not text.strip():
                message = f"Skipped document with empty or missing text: {document_path}"
                print(message)
                errors.append(message)
                continue

            document_chunks = chunk_text(
                clean_article(text, preserve_structure=True)
            )

            if max_chunks:
                remaining = max_chunks - len(chunks)
                document_chunks = document_chunks[:remaining]

            chunks.extend(document_chunks)
            usable_document_paths.append(str(document_path))
            processed_documents += 1

        if not chunks:
            message = f"No usable document text found for entity: {entity_directory.name}"
            print(message)
            errors.append(message)
            continue

        entity_name = entity_directory.name
        article_chunks[entity_name] = chunks
        output_filename_stems[entity_name] = entity_name
        source_document_paths[entity_name] = usable_document_paths

        print(
            f"Chunked entity {entity_name}: "
            f"{len(document_paths)} document files, {len(chunks)} chunks."
        )

    print(
        f"Finished raw document chunking. Chunked {processed_documents} documents "
        f"into {len(article_chunks)} entities."
    )

    return {
        "article_chunks": article_chunks,
        "output_filename_stems": output_filename_stems,
        "source_document_paths": source_document_paths,
        "errors": errors,
    }

