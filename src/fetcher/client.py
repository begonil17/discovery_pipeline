import re
import time

from tavily import TavilyClient

from src.fetcher.schemas import Document

from urllib.parse import urlparse

from src.fetcher.prompt import (
    BATCH_PROMPT,
    EMPTY_FRAGMENT_MARKER,
    PROMPT,
)

from src.config.settings import (
    FETCHER_BATCH_SAFE_LENGTH,
    FETCHER_MODEL,
    FETCHER_SAFE_LENGTH,
)

from src.llm.client import (
    LLMClient,
    LLMEmptyResponseError,
)


PART_SEPARATOR = "===================="


class FetcherClient:

    def __init__(self):

        self.tavily = TavilyClient()

    def extract_source(self, url: str) -> str:
        return urlparse(url).netloc

    def normalized_domain(self, url: str) -> str:

        domain = urlparse(url).netloc.casefold()

        if "@" in domain:
            domain = domain.rsplit("@", 1)[-1]

        if ":" in domain:
            domain = domain.split(":", 1)[0]

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    def source_requires_cleaning(
        self,
        url: str,
    ) -> bool:

        domain = self.normalized_domain(url)

        noisy_source_markers = (
            "blog",
            "blogspot",
            "wordpress",
            "medium",
            "substack",
            "news",
            "haber",
            "gazete",
            "magazine",
            "dergi",
            "recipe",
            "recipes",
            "tarif",
            "yemek",
            "lezzet",
            "nefisyemek",
        )

        return any(
            marker in domain
            for marker in noisy_source_markers
        )

    def source_is_trusted_clean(
        self,
        url: str,
    ) -> bool:

        if self.source_requires_cleaning(url):
            return False

        domain = self.normalized_domain(url)

        trusted_domains = (
            "wikipedia.org",
            "britannica.com",
        )

        if any(
            domain == trusted_domain
            or domain.endswith(f".{trusted_domain}")
            for trusted_domain in trusted_domains
        ):
            return True

        labels = set(domain.split("."))

        if "gov" in labels:
            return True

        if "edu" in labels or "ac" in labels:
            return True

        if "museum" in labels:
            return True

        if "muze" in domain or "müze" in domain:
            return True

        return False

    def text_has_navigation_artifacts(
        self,
        text: str,
    ) -> bool:

        lowered = text.casefold()

        artifact_phrases = (
            "cookie",
            "çerez",
            "gizlilik politikası",
            "privacy policy",
            "advertisement",
            "advertisements",
            "reklam",
            "subscribe",
            "newsletter",
            "sign in",
            "log in",
            "login",
            "üye girişi",
            "ana sayfa",
            "menü",
            "related articles",
            "you may also like",
            "read more",
            "devamını oku",
            "yorumlar",
            "all rights reserved",
            "tüm hakları saklıdır",
            "share this",
            "social media",
        )

        artifact_count = sum(
            1
            for phrase in artifact_phrases
            if phrase in lowered
        )

        if artifact_count >= 2:
            return True

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if len(lines) < 20:
            return False

        navigation_like_lines = 0

        for line in lines:

            word_count = len(line.split())

            if (
                word_count <= 4
                and (
                    line.startswith("[")
                    or line.startswith("- [")
                    or line.startswith("* [")
                )
            ):
                navigation_like_lines += 1

        return navigation_like_lines / len(lines) > 0.35

    def text_has_non_knowledge_prose(
        self,
        text: str,
    ) -> bool:

        lowered = text.casefold()

        non_knowledge_phrases = (
            "i think",
            "i tried",
            "i love",
            "i loved",
            "my favorite",
            "personally",
            "in my opinion",
            "we think",
            "we loved",
            "we recommend",
            "our favorite",
            "book now",
            "visit us",
            "contact us",
            "call us",
            "try this today",
            "benim favorim",
            "bence",
            "denedim",
            "denedik",
            "çok sevdim",
            "çok sevdik",
            "tavsiye ederim",
            "tavsiye ederiz",
            "bize ulaşın",
            "rezervasyon",
            "hemen deneyin",
            "ziyaret edin",
        )

        return any(
            phrase in lowered
            for phrase in non_knowledge_phrases
        )

    def should_skip_llm_cleaning(
        self,
        url: str,
        text: str,
    ) -> bool:

        if not self.source_is_trusted_clean(url):
            return False

        if self.text_has_navigation_artifacts(text):
            return False

        if self.text_has_non_knowledge_prose(text):
            return False

        return True

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

    def format_batch_parts(
        self,
        chunks: list[str],
    ) -> str:

        parts = []

        for index, chunk in enumerate(chunks, start=1):

            parts.append(
                f"{PART_SEPARATOR}\n"
                f"PART {index}\n\n"
                f"{chunk}"
            )

        return "\n\n".join(parts)

    def parse_cleaned_batch(
        self,
        text: str,
        expected_parts: int,
    ) -> list[str] | None:

        pattern = re.compile(
            rf"(?m)^{re.escape(PART_SEPARATOR)}\s*\n"
            r"PART\s+(\d+)\s*$"
        )

        matches = list(pattern.finditer(text))

        if len(matches) != expected_parts:
            return None

        parts: list[str | None] = [
            None
            for _ in range(expected_parts)
        ]

        for position, match in enumerate(matches):

            part_number = int(match.group(1))

            if (
                part_number < 1
                or part_number > expected_parts
                or parts[part_number - 1] is not None
            ):
                return None

            start = match.end()

            if position + 1 < len(matches):
                end = matches[position + 1].start()
            else:
                end = len(text)

            part = text[start:end].strip()

            if part == EMPTY_FRAGMENT_MARKER:
                part = ""

            parts[part_number - 1] = part

        if any(part is None for part in parts):
            return None

        return [
            part
            for part in parts
            if part is not None
        ]

    def clean_text_batch(
        self,
        chunks: list[str],
    ) -> list[str]:

        if not chunks:
            return []

        client = LLMClient()

        prompt = BATCH_PROMPT.format(

            text=self.format_batch_parts(chunks),
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
                "preserving the original batch."
            )

            return chunks

        parsed = self.parse_cleaned_batch(
            cleaned,
            len(chunks),
        )

        if parsed is None:

            print(
                "Could not parse batched cleaning response; "
                "preserving the original chunks."
            )

            return chunks

        return parsed

    def batch_chunks(
        self,
        chunks: list[str],
    ) -> list[list[str]]:

        batches = []
        current_batch = []
        current_size = 0

        for chunk in chunks:

            estimated_part_size = (
                len(chunk)
                + len(PART_SEPARATOR)
                + len("PART 0000")
                + 4
            )

            if (
                current_batch
                and current_size + estimated_part_size
                > FETCHER_BATCH_SAFE_LENGTH
            ):
                batches.append(current_batch)
                current_batch = []
                current_size = 0

            current_batch.append(chunk)
            current_size += estimated_part_size

        if current_batch:
            batches.append(current_batch)

        return batches

    def clean_chunks_in_batches(
        self,
        chunks: list[str],
    ) -> list[str]:

        batches = self.batch_chunks(chunks)
        cleaned_chunks = []

        for batch_index, batch in enumerate(
            batches,
            start=1,
        ):

            start_index = len(cleaned_chunks) + 1
            end_index = start_index + len(batch) - 1

            print(
                f"Cleaning batch {batch_index}/{len(batches)} "
                f"(chunks {start_index}-{end_index})..."
            )

            for offset, chunk in enumerate(batch):

                chunk_index = start_index + offset

                print(
                    f"Cleaning chunk {chunk_index}/{len(chunks)}..."
                )
                print(
                    f"Chunk {chunk_index} size: {len(chunk)}"
                )

            cleaned_batch = self.clean_text_batch(batch)

            for offset, cleaned_chunk in enumerate(
                cleaned_batch
            ):

                chunk_index = start_index + offset

                print(
                    f"Cleaned chunk {chunk_index} size: "
                    f"{len(cleaned_chunk)}"
                )

                cleaned_chunks.append(cleaned_chunk)

        return cleaned_chunks

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

        if self.should_skip_llm_cleaning(
            url,
            text,
        ):

            print(
                "Skipping LLM cleaning: "
                "extracted text appears clean."
            )

            cleaned = text

            print("Chunk count: 1")
            print(f"Merged length: {len(cleaned)}")
            print(f"Cleaned length: {len(cleaned)}")

            return Document(
                url=url,
                title=title,
                text=cleaned,
                source=self.extract_source(url),
            )

        if len(text) <= FETCHER_SAFE_LENGTH:

            print("Chunk count: 1")
            print("Cleaning chunk 1/1...")
            print(f"Chunk 1 size: {len(text)}")

            cleaned = self.clean_text(text)

            print(
                f"Cleaned chunk 1 size: "
                f"{len(cleaned)}"
            )

        else:

            chunks = self.split_markdown(text)

            print(f"Chunk count: {len(chunks)}")

            cleaned_chunks = self.clean_chunks_in_batches(
                chunks
            )

            cleaned = "\n\n".join(cleaned_chunks)

        print(f"Merged length: {len(cleaned)}")
        print(f"Cleaned length: {len(cleaned)}")

        return Document(
            url=url,
            title=title,
            text=cleaned,
            source=self.extract_source(url),
        )
