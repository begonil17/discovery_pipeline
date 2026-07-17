import json
import os
import re
import time

from src.nugget_pipeline.config import DATA_DIR
from src.nugget_pipeline.env import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

BAD_OUTPUT_DIR = DATA_DIR / "debug" / "llm_bad_outputs"
BAD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _save_bad_output(text: str):
    debug_path = BAD_OUTPUT_DIR / "bad_json_output.txt"
    debug_path.write_text(text, encoding="utf-8")
    return debug_path


def _extract_json(text: str):
    original_text = text
    text = text.strip()

    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    json_start = min(
        [index for index in (text.find("["), text.find("{")) if index != -1],
        default=-1,
    )
    if json_start != -1:
        decoder = json.JSONDecoder()

        try:
            parsed, end = decoder.raw_decode(text[json_start:])
            trailing_text = text[json_start + end:].strip()
            if trailing_text:
                print(
                    "[llm] WARNING: Ignoring text after first valid JSON value. "
                    f"Trailing text starts with: {trailing_text[:120]!r}"
                )
            return parsed
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            debug_path = _save_bad_output(original_text)
            raise ValueError(
                f"LLM returned invalid JSON. Saved raw output to {debug_path}. "
                f"JSON error: {e}"
            ) from e

    debug_path = _save_bad_output(original_text)
    raise ValueError(f"LLM did not return JSON. Saved raw output to {debug_path}.")


def _with_retries(call_fn, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return call_fn()
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt
            print(f"LLM call failed: {e}")
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)


def generate_json(prompt: str, model_name: str, schema: dict | None = None):
    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60,
            max_retries=2,
        )

        kwargs = {
            "model": model_name,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON. Do not use markdown.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }

        if schema is None:
            kwargs["response_format"] = {"type": "json_object"}

        def call_and_parse():
            response = client.chat.completions.create(**kwargs)
            return _extract_json(response.choices[0].message.content)

        return _with_retries(call_and_parse)

    elif LLM_PROVIDER == "gemini":
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        model = genai.GenerativeModel(model_name)

        generation_config = {
            "temperature": 0,
            "response_mime_type": "application/json",
        }

        if schema is not None:
            generation_config["response_schema"] = schema

        def call_and_parse():
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )

            try:
                text = response.text
            except ValueError as e:
                raise ValueError(
                    "Gemini returned no text. This may be a safety/copyright "
                    f"block. Original error: {e}"
                ) from e

            return _extract_json(text)

        return _with_retries(call_and_parse)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


