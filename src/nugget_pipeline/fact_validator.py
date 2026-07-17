import json

from src.nugget_pipeline.config import NUGGET_EXTRACTION_MODEL
from src.nugget_pipeline.llm.client import generate_json
from src.nugget_pipeline.schemas import FactValidation
from src.nugget_pipeline.llm.schemas import FACT_VALIDATION_SCHEMA


def validate_nuggets_against_chunk(
    article_title: str,
    chunk: str,
    nuggets: list[dict],
) -> list[dict]:
    if not nuggets:
        return []

    prompt = f"""
You are validating extracted Turkish atomic knowledge nuggets against their original source text chunk.

Document/entity title:
{article_title}

Original source text chunk:
{chunk}

Extracted nuggets:
{json.dumps(nuggets, ensure_ascii=False, indent=2)}

For each nugget, decide whether it is supported by the original chunk.

Verdicts:
- supported: the nugget is clearly supported by the chunk
- partially_supported: the nugget is mostly correct but needs rewriting to be fully supported
- unsupported: the nugget is not supported by the chunk

Rules:
- Do not use external knowledge.
- corrected_text must be Turkish.
- corrected_text must contain only the supported version of the fact.
- For recipe, procedure, list, timeline, or other ordered-flow nuggets, keep
  supported ingredients/materials, quantities, times, temperatures, conditions,
  tools, and ordering cues instead of replacing them with a vague summary.
- If unsupported, corrected_text should be an empty string.
- Return ONLY valid JSON array.

"""

    raw = generate_json(
        prompt=prompt,
        model_name=NUGGET_EXTRACTION_MODEL,
        schema=FACT_VALIDATION_SCHEMA
    )

    validations = [FactValidation(**item) for item in raw]

    validated_nuggets = []

    for validation in validations:
        original = next(
            (n for n in nuggets if n["nugget_id"] == validation.nugget_id),
            None,
        )

        if original is None:
            continue

        if validation.verdict == "unsupported":
            continue

        updated = dict(original)
        updated["text"] = validation.corrected_text
        updated["validation_verdict"] = validation.verdict
        updated["validation_reason"] = validation.reason

        validated_nuggets.append(updated)

    return validated_nuggets


