import re
import time

from tavily import TavilyClient

from src.fetcher.schemas import Document

from urllib.parse import urlparse

from src.fetcher.prompt import (
    EMPTY_FRAGMENT_MARKER,
    PROMPT,
)

from src.config.settings import FETCHER_MODEL

from src.llm.client import (
    LLMClient,
    LLMEmptyResponseError,
)


CHUNK_THRESHOLD = 4000


class FetcherClient:

    def __init__(self):

        self.tavily = TavilyClient()

    def extract_source(self, url: str) -> str:
        return urlparse(url).netloc

    def extract_from_tavily(
        self,
        url: str,
    ) -> tuple[str, str]:

        retries = 3

        for attempt in range(retries):

            try:

                response = self.tavily.extract(
                    urls=url,
                    extract_depth="advanced",
                    format="markdown",
                    timeout=30,
                )

                results = response.get(
                    "results",
                    [],
                )

                if not results:

                    failed_results = response.get(
                        "failed_results",
                        [],
                    )

                    raise ValueError(
                        "Tavily returned no extraction results. "
                        f"Failed results: {failed_results}"
                    )

                result = max(
                    results,
                    key=lambda item: len(
                        item.get(
                            "raw_content",
                            "",
                        )
                        or ""
                    ),
                )

                extracted_text = (
                    result.get(
                        "raw_content",
                        "",
                    )
                    or ""
                ).strip()

                title = (
                    result.get(
                        "title",
                        "",
                    )
                    or ""
                ).strip()

                if not title:

                    heading = re.search(
                        r"(?m)^#\s+(.+?)\s*$",
                        extracted_text,
                    )

                    if heading:
                        title = heading.group(1).strip()

                return title, extracted_text

            except Exception:

                if attempt == retries - 1:
                    raise

                wait = 2 ** attempt

                print(
                    "Tavily extraction failed "
                    f"({attempt + 1}/{retries})"
                )

                time.sleep(wait)

    def split_markdown(
        self,
        markdown: str,
    ) -> list[str]:

        max_chunk_size = 4000
        fallback_chunk_size = 3500
        overlap = 200

        if not markdown:
            return []

        def split_with_overlap(text: str) -> list[str]:

            chunks = []
            start = 0

            while start < len(text):

                end = min(
                    start + fallback_chunk_size,
                    len(text),
                )

                chunks.append(text[start:end])

                if end == len(text):
                    break

                start = end - overlap

            return chunks

        heading_starts = [
            match.start()
            for match in re.finditer(
                r"(?m)^#+",
                markdown,
            )
        ]

        if not heading_starts:
            return split_with_overlap(markdown)

        section_starts = heading_starts

        if heading_starts[0] != 0:
            section_starts = [0, *heading_starts]

        sections = [
            markdown[start:end]
            for start, end in zip(
                section_starts,
                [*section_starts[1:], len(markdown)],
            )
        ]

        chunks = []
        current_sections = []
        current_size = 0

        for section in sections:

            if len(section) > max_chunk_size:

                if current_sections:
                    chunks.append("".join(current_sections))
                    current_sections = []
                    current_size = 0

                chunks.extend(split_with_overlap(section))
                continue

            if (
                current_sections
                and current_size + len(section) > max_chunk_size
            ):
                chunks.append("".join(current_sections))
                current_sections = []
                current_size = 0

            current_sections.append(section)
            current_size += len(section)

        if current_sections:
            chunks.append("".join(current_sections))

        return chunks

    def clean_text(self, text: str) -> str:

        client = LLMClient()

        prompt = PROMPT.format(

            text=text,
            empty_fragment_marker=EMPTY_FRAGMENT_MARKER,

        )

        try:

            cleaned = client.generate(
                prompt=prompt,
                model_name=FETCHER_MODEL,
            )

        except LLMEmptyResponseError:

            print(
                "LLM returned no text after retries; "
                "preserving the original chunk."
            )

            return text

        if cleaned.strip() == EMPTY_FRAGMENT_MARKER:
            return ""

        return cleaned

    def fetch(self, url: str) -> Document | None:

        print(f"Fetching from Tavily... {url}")

        try:

            title, text = self.extract_from_tavily(url)

        except Exception as e:

            print(f"Failed to extract from Tavily: {url}")

            print(e)

            return None

        print(f"Extracted length: {len(text)}")

        if not text:
            return None

        if len(text) <= CHUNK_THRESHOLD:
            chunks = [text]
        else:
            chunks = self.split_markdown(text)

        print(f"Chunk count: {len(chunks)}")

        cleaned_chunks = []

        for index, chunk in enumerate(chunks, start=1):

            print(
                f"Cleaning chunk {index}/{len(chunks)}..."
            )
            print(f"Chunk {index} size: {len(chunk)}")

            cleaned_chunk = self.clean_text(chunk)

            print(
                f"Cleaned chunk {index} size: "
                f"{len(cleaned_chunk)}"
            )

            cleaned_chunks.append(cleaned_chunk)

        cleaned = "\n\n".join(cleaned_chunks)
        print(f"Merged length: {len(cleaned)}")
        print(f"Cleaned length: {len(cleaned)}")

        return Document(
            url=url,
            title=title,
            text=cleaned,
            source=self.extract_source(url),
        )
