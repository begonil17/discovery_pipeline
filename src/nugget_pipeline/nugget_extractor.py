import json
from uuid import uuid4

from src.nugget_pipeline.env import load_dotenv
from src.nugget_pipeline.llm.client import generate_json
from src.nugget_pipeline.config import NUGGET_EXTRACTION_MODEL
from src.nugget_pipeline.schemas import Nugget
from src.nugget_pipeline.llm.schemas import NUGGET_EXTRACTION_SCHEMA

load_dotenv()

def make_nugget_id() -> str:
    return f"ng_{uuid4().hex[:12]}"

def update_nuggets_with_chunk(
    article_title: str,
    chunk: str,
    current_nuggets: list[dict],
    max_nuggets: int = 10,
    retain_source_details: bool = False,
) -> list[dict]:
    selection_rule = (
        "- Preserve all distinct factual details that represent the source, "
        "including names, dates, locations, quantities, actions, and outcomes.\n"
        "- Preserve continuous/procedural information. For recipes, ingredient "
        "lists, instructions, timelines, or other ordered flows, extract the "
        "details needed to reconstruct the source flow: ingredients/materials, "
        "quantities, temperatures, timing, tools, conditions, decisions, "
        "actions, and order.\n"
        "- For ordered steps, create separate atomic nuggets that include the "
        "step number or ordering cue when the source provides or implies one.\n"
        "- Do not replace a list, recipe, procedure, or sequence with a single "
        "summary nugget.\n"
        "- Treat required ingredients, measurements, timings, temperatures, "
        "and ordered actions as important even when they look small in "
        "isolation.\n"
        "- Exclude only repetitive, unsupported, purely promotional, or "
        "meaningless details."
        if retain_source_details
        else "- Keep only important general-purpose knowledge."
    )

    prompt = f"""
You are extracting compact atomic knowledge nuggets from source documents.

Document/entity title: {article_title}

Current nugget list:
{json.dumps(current_nuggets, ensure_ascii=False, indent=2)}

New source text chunk:
{chunk}

Update the nugget list using the new chunk.

Rules:
- Output Turkish nuggets.
- Each nugget must be atomic: one clear paraphrased fact only.
- Avoid long direct translations or close paraphrases of source sentences.
- Avoid duplicates.
- Merge overlapping facts.
- Keep existing nuggets unless this chunk directly adds, corrects, or merges information.
- Return only new nuggets from this chunk and current nuggets that must be rewritten or merged.
- If you rewrite or merge a current nugget, preserve its existing nugget_id.
{selection_rule}
- Return at most {max_nuggets} new or modified nuggets for this chunk.
- Order by importance.
- importance must be an integer from 1 to 10.
- Return ONLY valid JSON array.

"""

    raw = generate_json(
        prompt=prompt,
        model_name=NUGGET_EXTRACTION_MODEL,
        schema=NUGGET_EXTRACTION_SCHEMA
        )

    for item in raw:
        if 'nugget_id' not in item or not item['nugget_id']:
            item['nugget_id'] = make_nugget_id()
        
        item['source_article'] = article_title
        

    validated = [Nugget(**item) for item in raw]

    return [item.model_dump() for item in validated]


