import json
import os
import re
import time
from typing import Type

from dotenv import load_dotenv
from pydantic import BaseModel

from src.config.settings import (
    DATA_DIR,
    LLM_PROVIDER,
    REQUEST_TIMEOUT,
)

load_dotenv()


BAD_OUTPUT_DIR = DATA_DIR / "debug" / "llm_bad_outputs"
BAD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class LLMEmptyResponseError(ValueError):
    pass


def _save_bad_output(text: str):

    debug_path = BAD_OUTPUT_DIR / "bad_json_output.txt"

    debug_path.write_text(
        text,
        encoding="utf-8",
    )

    return debug_path


def _extract_json(text: str):

    original_text = text

    text = text.strip()

    # Remove markdown fences if present
    match = re.search(
        r"```(?:json)?\s*(.*?)```",
        text,
        re.DOTALL,
    )

    if match:

        text = match.group(1).strip()

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        pass

    # Fallback: find first JSON object or array
    match = re.search(
        r"(\{.*\}|\[.*\])",
        text,
        re.DOTALL,
    )

    if match:

        candidate = match.group(1).strip()

        try:

            return json.loads(candidate)

        except json.JSONDecodeError as e:

            debug_path = _save_bad_output(original_text)

            raise ValueError(
                f"Invalid JSON returned by LLM. "
                f"Saved raw output to {debug_path}. "
                f"JSON error: {e}"
            ) from e

    debug_path = _save_bad_output(original_text)

    raise ValueError(
        f"LLM did not return JSON. "
        f"Saved raw output to {debug_path}."
    )


def _with_retries(call_fn, retries=3):

    for attempt in range(retries):

        try:

            return call_fn()

        except Exception as e:

            if attempt == retries - 1:

                raise

            wait = 2 ** attempt

            print(f"LLM call failed: {e}")

            print(f"Retrying in {wait} seconds...")

            time.sleep(wait)


class LLMClient:

    def __init__(self):

        self.provider = LLM_PROVIDER

    def generate(
        self,
        prompt: str,
        model_name: str,
    ) -> str:

        if self.provider == "openai":

            return self._openai_text(
                prompt,
                model_name,
            )

        elif self.provider == "gemini":

            return self._gemini_text(
                prompt,
                model_name,
            )

        raise ValueError(
            f"Unknown provider: {self.provider}"
        )

    def generate_structured(
        self,
        prompt: str,
        model_name: str,
        output_model: Type[BaseModel],
    ):

        if self.provider == "openai":

            return self._openai_structured(
                prompt,
                model_name,
                output_model,
            )

        elif self.provider == "gemini":

            return self._gemini_structured(
                prompt,
                model_name,
                output_model,
            )

        raise ValueError(
            f"Unknown provider: {self.provider}"
        )

    def _openai_text(
        self,
        prompt,
        model_name,
    ):

        from openai import OpenAI

        client = OpenAI(

            api_key=os.getenv("OPENAI_API_KEY"),

            timeout=REQUEST_TIMEOUT,

            max_retries=2,

        )

        response = _with_retries(

            lambda: client.chat.completions.create(

                model=model_name,

                temperature=0,

                messages=[

                    {
                        "role": "user",
                        "content": prompt,
                    },

                ],

            )

        )

        text = response.choices[0].message.content

        if not text or not text.strip():

            raise LLMEmptyResponseError(
                "OpenAI returned no text."
            )

        return text.strip()

    def _openai_structured(
        self,
        prompt,
        model_name,
        output_model,
    ):

        from openai import OpenAI

        client = OpenAI(

            api_key=os.getenv("OPENAI_API_KEY"),

            timeout=REQUEST_TIMEOUT,

            max_retries=2,

        )

        response = _with_retries(

            lambda: client.chat.completions.create(

                model=model_name,

                temperature=0,

                response_format={
                    "type": "json_object"
                },

                messages=[

                    {
                        "role": "system",
                        "content":
                        "Return ONLY valid JSON.",
                    },

                    {
                        "role": "user",
                        "content": prompt,
                    },

                ],

            )

        )

        data = _extract_json(

            response.choices[0].message.content

        )

        return output_model.model_validate(data)

    def _gemini_text(
        self,
        prompt,
        model_name,
    ):

        import google.generativeai as genai

        genai.configure(

            api_key=os.getenv("GEMINI_API_KEY")

        )

        model = genai.GenerativeModel(

            model_name

        )

        generation_config = {

            "temperature": 0,

            "max_output_tokens": 8192,

        }

        def generate_text():

            response = model.generate_content(

                prompt,

                generation_config=generation_config,

            )

            print("=" * 80)
            print(response)
            print("=" * 80)

            print("Candidates:", response.candidates)

            finish_reason = None

            if response.candidates:
                finish_reason = response.candidates[0].finish_reason

                print("Finish reason:", finish_reason)

                if hasattr(response.candidates[0], "safety_ratings"):
                    print(response.candidates[0].safety_ratings)

            try:

                text = response.text

            except ValueError as e:

                raise LLMEmptyResponseError(

                    "Gemini returned no text "
                    f"(finish_reason={finish_reason})."

                ) from e

            if not text or not text.strip():

                raise LLMEmptyResponseError(

                    "Gemini returned no text "
                    f"(finish_reason={finish_reason})."

                )

            return text.strip()

        return _with_retries(generate_text)

    def _gemini_structured(
        self,
        prompt,
        model_name,
        output_model,
    ):

        import google.generativeai as genai

        genai.configure(

            api_key=os.getenv("GEMINI_API_KEY")

        )

        model = genai.GenerativeModel(

            model_name

        )

        generation_config = {

            "temperature": 0,

            "response_mime_type": "application/json",

        }

        response = _with_retries(

            lambda: model.generate_content(

                prompt,

                generation_config=generation_config,

            )

        )

        try:

            text = response.text

        except ValueError as e:

            raise ValueError(

                "Gemini returned no text."

            ) from e

        data = _extract_json(text)

        return output_model.model_validate(data)
