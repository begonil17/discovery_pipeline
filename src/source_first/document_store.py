import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from src.config.settings import DATA_DIR
from src.fetcher.schemas import Document
from src.fetcher.saver import sanitize_filename
from src.source_first.schemas import (
    CandidateItem,
    CollectionObjective,
    NormalizedDocument,
    SourceProfile,
)


RAW_DOCUMENT_DIR = DATA_DIR / "raw_documents"


def content_hash_for(
    text: str,
) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def document_id_for(
    candidate: CandidateItem,
) -> str:
    raw = (
        f"{candidate.topic}|"
        f"{candidate.information_need}|"
        f"{candidate.source_id}|"
        f"{candidate.url}"
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()[:24]


def normalize_source_domain(
    url: str,
) -> str:
    domain = urlparse(url).netloc.casefold()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


class RawDocumentStore:
    def __init__(
        self,
        root: Path = RAW_DOCUMENT_DIR,
    ):
        self.root = root

    def topic_dir(
        self,
        topic: str,
    ) -> Path:
        path = self.root / sanitize_filename(topic)
        path.mkdir(
            parents=True,
            exist_ok=True,
        )
        return path

    def path_for(
        self,
        candidate: CandidateItem,
    ) -> Path:
        filename = (
            sanitize_filename(candidate.source_domain)
            + "__"
            + document_id_for(candidate)
            + ".json"
        )

        return self.topic_dir(candidate.topic) / filename

    def exists(
        self,
        candidate: CandidateItem,
    ) -> bool:
        return self.path_for(candidate).is_file()

    def load_for_candidate(
        self,
        candidate: CandidateItem,
    ) -> NormalizedDocument | None:
        path = self.path_for(candidate)

        if not path.is_file():
            return None

        with path.open(
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)

        try:
            return NormalizedDocument.model_validate(data)
        except Exception:
            return None

    def normalize(
        self,
        candidate: CandidateItem,
        source: SourceProfile,
        objective: CollectionObjective,
        document: Document,
    ) -> NormalizedDocument:
        content_hash = content_hash_for(document.text)

        return NormalizedDocument(
            document_id=document_id_for(candidate),
            topic=candidate.topic,
            information_need=candidate.information_need,
            source=normalize_source_domain(candidate.url),
            source_id=source.source_id,
            source_url=candidate.url,
            title=document.title or candidate.title,
            text=document.text,
            published_at=candidate.published_at,
            updated_at=candidate.updated_at,
            fetched_at=datetime.now(timezone.utc),
            popularity_metadata=candidate.popularity,
            content_hash=content_hash,
            status="active",
            candidate_id=candidate.candidate_id,
            metadata={
                "collection_objective": objective.model_dump(
                    mode="json"
                ),
                "candidate": candidate.model_dump(mode="json"),
                "source_profile": {
                    "source_id": source.source_id,
                    "domain": source.domain,
                    "authority_score": source.authority_score,
                    "update_frequency": source.update_frequency,
                    "popularity_metric": source.popularity_metric,
                },
            },
        )

    def save(
        self,
        normalized: NormalizedDocument,
    ) -> Path:
        topic_dir = self.topic_dir(normalized.topic)
        filename = (
            sanitize_filename(normalized.source)
            + "__"
            + normalized.document_id
            + ".json"
        )
        path = topic_dir / filename

        data = normalized.model_dump(mode="json")

        # Preserve the old raw document surface while adding provenance.
        ordered_data = {
            "title": data.pop("title"),
            "text": data.pop("text"),
            **data,
        }

        temp_path = path.with_name(f"{path.name}.tmp")

        with temp_path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                ordered_data,
                f,
                ensure_ascii=False,
                indent=4,
            )

        temp_path.replace(path)

        return path
