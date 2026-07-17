import json

from src.nugget_pipeline.env import load_dotenv
from src.nugget_pipeline.llm.client import generate_json
from src.nugget_pipeline.config import RAW_QA_MODEL
from src.nugget_pipeline.schemas import RawQAPair

load_dotenv()

def generate_raw_qa_from_chunk(
    article_title: str,
    chunk: str,
    questions_per_chunk: int = 3,
) -> list[dict]:

    prompt = f"""
You are creating Turkish QA pairs directly from a Wikipedia article chunk.

Article title: {article_title}

Article chunk:
{chunk}

Generate up to {questions_per_chunk} high-quality Turkish QA pairs.

Rules:
- Questions and answers must be in Turkish.
- Each answer must be directly supported by the chunk.
- Prefer important, general-purpose information.
- Avoid trivial details.
- Avoid duplicate questions.
- importance must be an integer from 1 to 10.
- Return ONLY valid JSON array.

Format:
[
  {{
    "question": "...",
    "answer": "...",
    "source_article": "{article_title}",
    "importance": 1,
    "storage_type": "raw_qa"
  }}
]
"""

    raw = generate_json(
            prompt=prompt,
            model_name=RAW_QA_MODEL,
        )

    validated = [RawQAPair(**item) for item in raw]

    return [item.model_dump() for item in validated]


