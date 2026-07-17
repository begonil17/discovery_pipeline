import json
from pathlib import Path

from src.persistence.manifest import (
    atomic_write_json,
    load_json,
    relative_path,
    utc_now_iso,
)
from src.nugget_pipeline.config import DATA_DIR, OUTPUT_DIR, NUGGET_MANIFEST_PATH
from src.nugget_pipeline.fact_validator import validate_nuggets_against_chunk
from src.nugget_pipeline.nugget_extractor import update_nuggets_with_chunk
from src.nugget_pipeline.qa_generator import generate_qa_from_nuggets
from src.nugget_pipeline.storage_decision import (
    decide_nugget_storage,
    fallback_keep_top_candidates,
)


NUGGET_DIR = OUTPUT_DIR / "nugget_discovery"
NUGGET_QA_DIR = OUTPUT_DIR / "nugget_qa_discovery"

NUGGET_DIR.mkdir(parents=True, exist_ok=True)
NUGGET_QA_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(title: str) -> str:
    return (
        title
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def output_filename_stem(state, title: str) -> str:
    requested_stem = state.get("output_filename_stems", {}).get(title)

    if (
        isinstance(requested_stem, str)
        and requested_stem
        and "/" not in requested_stem
        and "\\" not in requested_stem
        and requested_stem not in {".", ".."}
    ):
        return requested_stem

    return safe_filename(title)


def output_directories(state):
    nugget_dir = Path(state.get("nugget_output_dir") or NUGGET_DIR)
    nugget_qa_dir = Path(state.get("nugget_qa_output_dir") or NUGGET_QA_DIR)
    nugget_dir.mkdir(parents=True, exist_ok=True)
    nugget_qa_dir.mkdir(parents=True, exist_ok=True)
    return nugget_dir, nugget_qa_dir


def nugget_manifest_path(state) -> Path:
    configured_path = (
        state.get("nugget_manifest_path")
        or state.get("qa_manifest_path")
        or NUGGET_MANIFEST_PATH
    )
    return Path(configured_path)


def load_nugget_manifest(state) -> dict:
    manifest = load_json(
        nugget_manifest_path(state),
        {
            "version": 1,
            "entities": {},
        },
    )

    if not isinstance(manifest, dict):
        manifest = {
            "version": 1,
            "entities": {},
        }

    manifest.setdefault("version", 1)
    manifest.setdefault("entities", {})
    return manifest


def save_nugget_manifest(state, manifest: dict) -> None:
    manifest["updated_at"] = utc_now_iso()
    atomic_write_json(nugget_manifest_path(state), manifest)


def record_nugget_manifest(
    state,
    manifest: dict,
    article_key: str,
    title: str,
    nugget_path: Path,
    nugget_qa_path: Path,
    nuggets: list[dict],
    qa_count: int,
    chunk_count: int,
    source_document_paths: list[str],
    status: str,
) -> None:
    manifest.setdefault("entities", {})[article_key] = {
        "title": title,
        "status": status,
        "nugget_path": relative_path(nugget_path, DATA_DIR),
        "nugget_qa_path": relative_path(nugget_qa_path, DATA_DIR),
        "nugget_ids": nugget_ids(nuggets),
        "nugget_count": len(nuggets),
        "qa_count": qa_count,
        "chunk_count": chunk_count,
        "source_document_paths": [
            relative_path(Path(path), DATA_DIR)
            for path in source_document_paths
        ],
        "updated_at": utc_now_iso(),
    }
    save_nugget_manifest(state, manifest)


def record_recoverable_error(errors: list[str], message: str, exc: Exception):
    error_message = f"{message}: {exc}"
    errors.append(error_message)
    print(f"[nugget_qa] WARNING: {error_message}")


def entity_manifest_record(manifest: dict, article_key: str) -> dict:
    record = manifest.get("entities", {}).get(article_key, {})
    return record if isinstance(record, dict) else {}


def completed_outputs_exist(
    nugget_path: Path,
    nugget_qa_path: Path,
    manifest_record: dict | None = None,
) -> bool:
    if not (
        nugget_path.exists()
        and nugget_path.stat().st_size > 0
        and nugget_qa_path.exists()
    ):
        return False

    if nugget_qa_path.stat().st_size > 0:
        return True

    return (manifest_record or {}).get("status") == "completed"


def load_existing_nuggets(nugget_path: Path) -> list[dict] | None:
    if not nugget_path.exists() or nugget_path.stat().st_size == 0:
        return None

    try:
        data = json.loads(nugget_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None

    if not isinstance(data, list):
        return None

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0

    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return 0


def write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")

    with temporary_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    temporary_path.replace(path)


def nugget_importance(nugget):
    try:
        return int(nugget.get("importance", 0))
    except (TypeError, ValueError):
        return 0


def prune_nuggets_by_importance(nuggets, max_nuggets):
    return sorted(
        nuggets,
        key=nugget_importance,
        reverse=True,
    )[:max_nuggets]


def nugget_ids(nuggets):
    return [
        nugget.get("nugget_id")
        for nugget in nuggets
        if nugget.get("nugget_id")
    ]


def retain_supported_nuggets(nuggets):
    retained = []

    for nugget in nuggets:
        importance = nugget_importance(nugget)

        if importance >= 8:
            detail_level = "high"
            questions_per_nugget = 3
        elif importance >= 5:
            detail_level = "medium"
            questions_per_nugget = 2
        else:
            detail_level = "low"
            questions_per_nugget = 1

        retained.append(
            {
                **nugget,
                "detail_level": detail_level,
                "questions_per_nugget": questions_per_nugget,
                "storage_action": "keep_full",
                "storage_reason": (
                    "Retained because this pipeline keeps every factually "
                    "supported source nugget."
                ),
            }
        )

    return retained


def split_nuggets_for_chunk_validation(current_nuggets, extracted_nuggets):
    current_by_id = {
        nugget.get("nugget_id"): nugget
        for nugget in current_nuggets
        if nugget.get("nugget_id")
    }
    preserved_by_id = {
        nugget_id: dict(nugget)
        for nugget_id, nugget in current_by_id.items()
    }
    nuggets_to_validate = []

    for nugget in extracted_nuggets:
        nugget_id = nugget.get("nugget_id")
        previous = current_by_id.get(nugget_id)

        if previous is None:
            nuggets_to_validate.append(nugget)
            continue

        if nugget.get("text") == previous.get("text"):
            preserved_by_id[nugget_id] = dict(nugget)
        else:
            nuggets_to_validate.append(nugget)

    preserved_nuggets = []
    seen_ids = set()

    for nugget in current_nuggets:
        nugget_id = nugget.get("nugget_id")

        if not nugget_id:
            preserved_nuggets.append(dict(nugget))
            continue

        if nugget_id in preserved_by_id and nugget_id not in seen_ids:
            preserved_nuggets.append(preserved_by_id[nugget_id])
            seen_ids.add(nugget_id)

    return preserved_nuggets, nuggets_to_validate


def merge_validated_nuggets(preserved_nuggets, validated_nuggets):
    merged_nuggets = []
    index_by_id = {}

    for nugget in preserved_nuggets:
        nugget_id = nugget.get("nugget_id")
        if nugget_id and nugget_id not in index_by_id:
            index_by_id[nugget_id] = len(merged_nuggets)
        merged_nuggets.append(dict(nugget))

    for nugget in validated_nuggets:
        nugget_id = nugget.get("nugget_id")

        if nugget_id and nugget_id in index_by_id:
            merged_nuggets[index_by_id[nugget_id]] = dict(nugget)
            continue

        if nugget_id:
            index_by_id[nugget_id] = len(merged_nuggets)
        merged_nuggets.append(dict(nugget))

    return merged_nuggets


def extract_and_store_nuggets(
    state,
    errors: list[str],
    title: str,
    chunks: list[str],
) -> list[dict]:
    nuggets = []

    for chunk_index, chunk in enumerate(chunks, start=1):
        print(
            f"Starting nugget extraction chunk "
            f"{chunk_index}/{len(chunks)} for: {title}"
        )

        try:
            extracted_nuggets = update_nuggets_with_chunk(
                article_title=title,
                chunk=chunk,
                current_nuggets=nuggets,
                max_nuggets=state.get("max_nuggets_per_chunk", 5),
                retain_source_details=state.get(
                    "retain_source_details",
                    False,
                ),
            )
        except Exception as exc:
            record_recoverable_error(
                errors,
                (
                    "Skipping nugget extraction for "
                    f"{title}, chunk {chunk_index}/{len(chunks)}"
                ),
                exc,
            )
            continue

        print(
            f"Finished nugget extraction chunk "
            f"{chunk_index}/{len(chunks)} for: {title}. "
            f"Extracted {len(extracted_nuggets)} nuggets."
        )
        print(
            f"After chunk extraction for: {title}, "
            f"chunk {chunk_index}/{len(chunks)}. "
            f"Current count before extraction: {len(nuggets)}. "
            f"Extracted/updated IDs: {nugget_ids(extracted_nuggets)}"
        )

        preserved_nuggets, nuggets_to_validate = (
            split_nuggets_for_chunk_validation(
                current_nuggets=nuggets,
                extracted_nuggets=extracted_nuggets,
            )
        )

        print(
            f"Preparing validation chunk {chunk_index}/{len(chunks)} "
            f"for: {title}. Preserving {len(preserved_nuggets)} "
            f"previous/unchanged nuggets and validating "
            f"{len(nuggets_to_validate)} new/modified nuggets."
        )

        print(
            f"Starting nugget validation chunk "
            f"{chunk_index}/{len(chunks)} for: {title}"
        )

        try:
            validated_nuggets = validate_nuggets_against_chunk(
                article_title=title,
                chunk=chunk,
                nuggets=nuggets_to_validate,
            )
        except Exception as exc:
            record_recoverable_error(
                errors,
                (
                    "Skipping new/modified nuggets after validation "
                    f"failure for {title}, chunk "
                    f"{chunk_index}/{len(chunks)}"
                ),
                exc,
            )
            nuggets = preserved_nuggets
            continue

        print(
            f"Finished nugget validation chunk "
            f"{chunk_index}/{len(chunks)} for: {title}. "
            f"Validated {len(validated_nuggets)} nuggets."
        )
        print(
            f"After chunk validation for: {title}, "
            f"chunk {chunk_index}/{len(chunks)}. "
            f"Validated IDs: {nugget_ids(validated_nuggets)}"
        )

        nuggets = merge_validated_nuggets(
            preserved_nuggets=preserved_nuggets,
            validated_nuggets=validated_nuggets,
        )

        print(
            f"Accumulated nuggets after chunk {chunk_index}/{len(chunks)} "
            f"for: {title}: {len(nuggets)}. IDs: {nugget_ids(nuggets)}"
        )

    nuggets = prune_nuggets_by_importance(
        nuggets,
        state.get("max_nuggets_per_article", 20),
    )

    if state.get("retain_all_supported_nuggets", False):
        nuggets = retain_supported_nuggets(nuggets)
        print(
            f"Retained all {len(nuggets)} factually supported nuggets "
            f"for: {title}."
        )
    else:
        print(
            f"Before storage decision for: {title}. "
            f"Candidate nuggets: {len(nuggets)}. "
            f"IDs: {nugget_ids(nuggets)}"
        )

        print(f"Starting nugget storage decision for: {title}")

        try:
            nuggets = decide_nugget_storage(
                article_title=title,
                candidate_nuggets=nuggets,
                existing_nuggets=[],
            )
        except Exception as exc:
            record_recoverable_error(
                errors,
                (
                    "Storage decision failed; keeping top candidates "
                    f"with fallback for {title}"
                ),
                exc,
            )
            nuggets = fallback_keep_top_candidates(nuggets)

        print(
            f"Finished nugget storage decision for: {title}. "
            f"Keeping {len(nuggets)} nuggets."
        )
        print(
            f"After storage decision for: {title}. "
            f"Kept IDs: {nugget_ids(nuggets)}"
        )

    return nuggets


def nugget_qa_node(state):
    print("Starting nugget extraction and QA generation...")

    errors = list(state.get("errors", []))
    nugget_paths = []
    nugget_qa_paths = []
    nugget_dir, nugget_qa_dir = output_directories(state)
    article_titles = state.get("article_titles", {})
    source_paths_by_article = state.get("source_document_paths", {})
    manifest = load_nugget_manifest(state)

    for article_key, chunks in state["article_chunks"].items():
        title = article_titles.get(article_key, article_key)
        print(f"Starting nugget pipeline for: {title}")

        filename_stem = output_filename_stem(state, article_key)
        nugget_path = nugget_dir / f"{filename_stem}.json"
        nugget_qa_path = nugget_qa_dir / f"{filename_stem}.jsonl"
        source_document_paths = source_paths_by_article.get(article_key, [])
        manifest_record = entity_manifest_record(manifest, article_key)

        if completed_outputs_exist(
            nugget_path,
            nugget_qa_path,
            manifest_record,
        ):
            existing_nuggets = load_existing_nuggets(nugget_path) or []
            qa_count = count_jsonl_rows(nugget_qa_path)
            record_nugget_manifest(
                state=state,
                manifest=manifest,
                article_key=article_key,
                title=title,
                nugget_path=nugget_path,
                nugget_qa_path=nugget_qa_path,
                nuggets=existing_nuggets,
                qa_count=qa_count,
                chunk_count=len(chunks),
                source_document_paths=source_document_paths,
                status="completed",
            )
            nugget_paths.append(str(nugget_path))
            nugget_qa_paths.append(str(nugget_qa_path))
            print(f"Finished nugget pipeline for: {title} (cached)")
            continue

        existing_nuggets = load_existing_nuggets(nugget_path)
        if existing_nuggets is not None:
            nuggets = existing_nuggets
            print(
                f"Reusing {len(nuggets)} existing nuggets for: {title}. "
                f"IDs: {nugget_ids(nuggets)}"
            )
        else:
            nuggets = extract_and_store_nuggets(
                state=state,
                errors=errors,
                title=title,
                chunks=chunks,
            )
            atomic_write_json(nugget_path, nuggets)
            record_nugget_manifest(
                state=state,
                manifest=manifest,
                article_key=article_key,
                title=title,
                nugget_path=nugget_path,
                nugget_qa_path=nugget_qa_path,
                nuggets=nuggets,
                qa_count=count_jsonl_rows(nugget_qa_path),
                chunk_count=len(chunks),
                source_document_paths=source_document_paths,
                status="nuggets_written",
            )

        print(f"Starting nugget QA generation for: {title}")
        print(
            f"Before QA generation for: {title}. "
            f"Nuggets available: {len(nuggets)}. IDs: {nugget_ids(nuggets)}"
        )

        qa_status = "completed"
        try:
            qa_pairs = generate_qa_from_nuggets(nuggets)
        except Exception as exc:
            record_recoverable_error(
                errors,
                f"QA generation failed; writing nuggets without QA for {title}",
                exc,
            )
            qa_pairs = []
            qa_status = "qa_failed"

        print(
            f"Finished nugget QA generation for: {title}. "
            f"Generated {len(qa_pairs)} QA pairs."
        )

        write_jsonl_atomic(nugget_qa_path, qa_pairs)
        record_nugget_manifest(
            state=state,
            manifest=manifest,
            article_key=article_key,
            title=title,
            nugget_path=nugget_path,
            nugget_qa_path=nugget_qa_path,
            nuggets=nuggets,
            qa_count=len(qa_pairs),
            chunk_count=len(chunks),
            source_document_paths=source_document_paths,
            status=qa_status,
        )

        nugget_paths.append(str(nugget_path))
        nugget_qa_paths.append(str(nugget_qa_path))

        print(f"Finished nugget pipeline for: {title}")

    print(
        f"Finished nugget extraction and QA generation. "
        f"Created {len(nugget_paths)} nugget files and "
        f"{len(nugget_qa_paths)} QA files."
    )

    return {
        "nugget_paths": nugget_paths,
        "nugget_qa_paths": nugget_qa_paths,
        "errors": errors,
    }


