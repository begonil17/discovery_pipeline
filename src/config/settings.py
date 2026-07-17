import os
from pathlib import Path

# -----------------------
# Directories
# -----------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(
    os.getenv(
        "PIPELINE_DATA_DIR",
        PROJECT_ROOT / "data",
    )
).expanduser()

CACHE_DIR = DATA_DIR / "cache"

DISCOVERED_DIR = DATA_DIR / "discovered"

RAW_DOCUMENTS_DIR = DATA_DIR / "raw_documents"

OUTPUT_DIR = DATA_DIR / "output"

MANIFEST_DIR = DATA_DIR / "manifests"

DISCOVERY_MANIFEST_PATH = MANIFEST_DIR / "discovery_manifest.json"

NUGGET_MANIFEST_PATH = MANIFEST_DIR / "nugget_manifest.json"


# -----------------------
# Wikipedia
# -----------------------

USER_AGENT = (
    "KnowledgeBuilder/1.0 "
    "(Research project; "
    "contact: begum.atay0106@gmail.com)"
)

WIKIPEDIA_BATCH_SIZE = 50

REQUEST_TIMEOUT = 30

MAX_RETRIES = 3


# -----------------------
# Discovery
# -----------------------

DEFAULT_LANGUAGE = "tr"

DEFAULT_MAX_DEPTH = 2

DEFAULT_ENTITY_LIMIT = 300

# -----------------------
# LLM
# -----------------------

LLM_PROVIDER = "gemini"

PLANNER_MODEL = "gemini-3.5-pro"

SEARCH_MODEL = "gemini-3.5-flash"

FETCHER_MODEL = "gemini-3.5-flash"

REQUEST_TIMEOUT = 60

# -----------------------
# Fetcher
# -----------------------

FETCHER_SAFE_LENGTH = 12000

FETCHER_BATCH_SAFE_LENGTH = 12000

# -----------------------
# Future
# -----------------------

MAX_WORKERS = 8
