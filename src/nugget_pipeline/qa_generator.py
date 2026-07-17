import json

from src.nugget_pipeline.env import load_dotenv
from src.nugget_pipeline.llm.client import generate_json
from src.nugget_pipeline.config import NUGGET_QA_MODEL
from src.nugget_pipeline.schemas import FactLinkedQAPair
from src.nugget_pipeline.llm.schemas import NUGGET_QA_SCHEMA

load_dotenv()

def generate_qa_from_nuggets(nuggets: list[dict]) -> list[dict]:

    prompt = f"""
Generate Turkish QA pairs from these atomic knowledge nuggets.

Nuggets:
{json.dumps(nuggets, ensure_ascii=False, indent=2)}

Rules:
- Each question must be answerable only from its nugget.
- Avoid duplicate question wording.
- Answers should be short and clear.
- Preserve nugget_id in each QA pair.
- Return ONLY valid JSON array.
- Each nugget has questions_per_nugget.
- Generate exactly questions_per_nugget questions for each nugget.
- Do not generate questions for nuggets with questions_per_nugget = 0.

"""

    raw = generate_json(
          prompt=prompt,
          model_name=NUGGET_QA_MODEL,
          schema=NUGGET_QA_SCHEMA
        )
    
    source_by_nugget = {
        nugget["nugget_id"]: nugget.get("source_article", "")
        for nugget in nuggets
    }

    for item in raw:
        item["source_article"] = source_by_nugget.get(item["nugget_id"], "")
        item["storage_type"] = "nugget_qa"

    validated = [FactLinkedQAPair(**item) for item in raw]

    return [item.model_dump() for item in validated]


