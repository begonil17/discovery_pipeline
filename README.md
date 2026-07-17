# Discovery + Nugget Pipeline

This branch merges the discovery pipeline with the raw-document nugget pipeline.
Use `run_system.py` as the single entry point.

## Run

```powershell
python run_system.py discover --data-dir data
python run_system.py nugget --data-dir data
python run_system.py all --data-dir data
```

The `all` command runs discovery first, then uses `data/raw_documents` as the
input for nugget extraction and nugget-linked QA generation.

## Single Data Root

All generated state is kept under `--data-dir` or the `PIPELINE_DATA_DIR`
environment variable:

- `raw_documents/`: fetched source documents, grouped by entity
- `cache/`: cached discovery, enrichment, planner, and search stages
- `manifests/discovery_manifest.json`: fetched URL/file tracking
- `manifests/nugget_manifest.json`: nugget output, QA output, source files, and nugget IDs
- `output/nugget_discovery/`: extracted nuggets
- `output/nugget_qa_discovery/`: nugget-linked QA JSONL files
- `debug/`: LLM bad-output debug files

## Rerun Behavior

Discovery reruns use stage caches by default. Use the refresh flags when you
want to recompute a stage:

```powershell
python run_system.py discover --refresh-search
python run_system.py discover --refresh-fetch
python run_system.py discover --refresh
```

Fetching is tracked per URL. New raw-document filenames include a URL hash and
the saved JSON includes `url`, `source`, `title`, and `text`, so multiple URLs
from the same domain do not overwrite each other.

The nugget stage reuses existing nugget JSON files if QA generation was interrupted.
That preserves already assigned `nugget_id` values and regenerates only the
missing QA file.
