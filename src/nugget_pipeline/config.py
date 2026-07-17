import os
from pathlib import Path

from src.nugget_pipeline.env import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(
    os.getenv(
        "PIPELINE_DATA_DIR",
        PROJECT_ROOT / "data",
    )
).expanduser()

RAW_DOCUMENTS_DIR = DATA_DIR / "raw_documents"
OUTPUT_DIR = DATA_DIR / "output"
MANIFEST_DIR = DATA_DIR / "manifests"
NUGGET_MANIFEST_PATH = MANIFEST_DIR / "nugget_manifest.json"

TOPIC_SELECTION_MODEL = os.getenv("TOPIC_SELECTION_MODEL", "gpt-5.1")
RAW_QA_MODEL = os.getenv("RAW_QA_MODEL", "gpt-5.1")
NUGGET_EXTRACTION_MODEL = os.getenv("NUGGET_EXTRACTION_MODEL", "gpt-5.1")
NUGGET_QA_MODEL = os.getenv("NUGGET_QA_MODEL", "gpt-5.1")

