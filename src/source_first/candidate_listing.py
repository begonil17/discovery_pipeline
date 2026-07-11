import hashlib
import os
from urllib.parse import urlparse

from tavily import TavilyClient

from src.source_first.schemas import (
    CandidateItem,
    InformationNeed,
    SourceProfile,
    TopicPlan,
)


def normalize_domain(
    url_or_domain: str,
) -> str:
    parsed = urlparse(url_or_domain)
    domain = parsed.netloc or url_or_domain
    domain = domain.casefold()

    if "@" in domain:
        domain = domain.rsplit("@", 1)[-1]

    if ":" in domain:
        domain = domain.split(":", 1)[0]

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def candidate_id_for(
    source_id: str,
    information_need: str,
    url: str,
) -> str:
    raw = f"{source_id}|{information_need}|{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def domain_matches(
    candidate_domain: str,
    approved_domain: str,
) -> bool:
    candidate_domain = normalize_domain(candidate_domain)
    approved_domain = normalize_domain(approved_domain)

    return (
        candidate_domain == approved_domain
        or candidate_domain.endswith(f".{approved_domain}")
    )


class CandidateLister:
    def __init__(
        self,
        tavily: TavilyClient | None = None,
        max_results_per_source_need: int | None = None,
        max_sources_per_information_need: int | None = None,
        source_ids_by_information_need: dict | None = None,
        manual_candidates: list[dict] | None = None,
    ):
        self.tavily = tavily
        self.max_results_per_source_need = max_results_per_source_need
        self.max_sources_per_information_need = (
            max_sources_per_information_need
        )
        self.source_ids_by_information_need = (
            source_ids_by_information_need or {}
        )
        self.manual_candidates = manual_candidates or []

    def _tavily_client(self) -> TavilyClient:
        if self.tavily is None:
            self.tavily = TavilyClient(
                api_key=os.getenv("TAVILY_API_KEY")
            )

        return self.tavily

    def build_queries(
        self,
        topic: str,
        need: InformationNeed,
        source: SourceProfile,
    ) -> list[str]:
        query_intents = need.candidate_queries

        if query_intents:
            templates = [
                template
                for template in source.collection_strategy.search_templates
                if "{query}" in template
            ]

            if not templates:
                templates = [
                    "{query} site:{domain}",
                ]

            return [
                template.format(
                    query=query,
                    topic=topic,
                    information_need=need.name,
                    domain=source.domain,
                )
                for query in query_intents
                for template in templates
            ]

        templates = source.collection_strategy.search_templates

        if not templates:
            templates = [
                "{topic} {information_need} site:{domain}",
            ]

        return [
            template.format(
                topic=topic,
                information_need=need.name,
                domain=source.domain,
            )
            for template in templates
        ]

    def list_for_source_need(
        self,
        topic: str,
        need: InformationNeed,
        source: SourceProfile,
    ) -> list[CandidateItem]:
        if source.collection_strategy.method != "tavily_search":
            return []

        max_results = (
            self.max_results_per_source_need
            if self.max_results_per_source_need is not None
            else source.collection_strategy.max_candidates
        )

        candidates = []
        seen_urls = set()

        for query in self.build_queries(
            topic,
            need,
            source,
        ):
            response = self._tavily_client().search(
                query=query,
                max_results=max(1, int(max_results)),
            )

            for result in response.get("results", []):
                url = result.get("url", "")

                if not url or url in seen_urls:
                    continue

                if not domain_matches(
                    normalize_domain(url),
                    source.domain,
                ):
                    continue

                seen_urls.add(url)

                candidates.append(
                    CandidateItem(
                        candidate_id=candidate_id_for(
                            source.source_id,
                            need.name,
                            url,
                        ),
                        topic=topic,
                        information_need=need.name,
                        source_id=source.source_id,
                        source_domain=source.domain,
                        title=result.get("title") or url,
                        url=url,
                        popularity={},
                        estimated_cost=1.0,
                        metadata={
                            "query": query,
                            "tavily_score": result.get("score"),
                            "snippet": result.get("content"),
                        },
                    )
                )

        return candidates

    def source_ids_for_need(
        self,
        topic: str,
        need_name: str,
    ) -> list[str] | None:

        topic_config = self.source_ids_by_information_need.get(
            topic,
        )

        if topic_config is None:
            topic_config = self.source_ids_by_information_need.get(
                "*",
            )

        if topic_config is None:
            return None

        if isinstance(topic_config, list):
            return topic_config

        if not isinstance(topic_config, dict):
            return None

        source_ids = topic_config.get(need_name)

        if source_ids is None:
            source_ids = topic_config.get("*")

        if isinstance(source_ids, list):
            return source_ids

        return None

    def sources_for_need(
        self,
        topic: str,
        need: InformationNeed,
        sources: list[SourceProfile],
    ) -> list[SourceProfile]:

        allowed_source_ids = self.source_ids_for_need(
            topic,
            need.name,
        )

        if allowed_source_ids is not None:
            source_by_id = {
                source.source_id: source
                for source in sources
            }

            return [
                source_by_id[source_id]
                for source_id in allowed_source_ids
                if source_id in source_by_id
            ]

        matching = [
            source
            for source in sources
            if source.supports_need(
                topic,
                need.name,
            )
        ]

        matching = sorted(
            matching,
            key=lambda source: source.authority_score,
            reverse=True,
        )

        if self.max_sources_per_information_need is not None:
            matching = matching[
                : self.max_sources_per_information_need
            ]

        return matching

    def manual_candidates_for_need(
        self,
        topic: str,
        need: InformationNeed,
        sources: list[SourceProfile],
    ) -> list[CandidateItem]:

        source_by_id = {
            source.source_id: source
            for source in sources
        }

        candidates = []

        for item in self.manual_candidates:

            if not isinstance(item, dict):
                print("Skipping non-object manual candidate.")
                continue

            if item.get("topic") != topic:
                continue

            if item.get("information_need") != need.name:
                continue

            url = (item.get("url") or "").strip()
            source_id = (item.get("source_id") or "").strip()

            if not url or not source_id:
                print(
                    "Skipping manual candidate without url "
                    "or source_id."
                )
                continue

            source = source_by_id.get(source_id)

            if source is None:
                print(
                    "Skipping manual candidate with unknown "
                    f"source_id {source_id}: {url}"
                )
                continue

            metadata = item.get("metadata") or {}

            if not isinstance(metadata, dict):
                metadata = {}

            try:
                estimated_cost = float(
                    item.get("estimated_cost", 1.0)
                )

            except (TypeError, ValueError):
                estimated_cost = 1.0

            candidates.append(
                CandidateItem(
                    candidate_id=candidate_id_for(
                        source.source_id,
                        need.name,
                        url,
                    ),
                    topic=topic,
                    information_need=need.name,
                    source_id=source.source_id,
                    source_domain=source.domain,
                    title=item.get("title") or url,
                    url=url,
                    estimated_cost=estimated_cost,
                    metadata={
                        **metadata,
                        "manual": True,
                    },
                )
            )

        return candidates

    def list_candidates(
        self,
        topic_plan: TopicPlan,
        sources: list[SourceProfile],
    ) -> list[CandidateItem]:
        candidates = []
        seen_keys = set()

        for need in topic_plan.information_needs:
            for candidate in self.manual_candidates_for_need(
                topic_plan.topic,
                need,
                sources,
            ):
                key = (
                    candidate.information_need,
                    candidate.url,
                )

                if key in seen_keys:
                    continue

                seen_keys.add(key)
                candidates.append(candidate)

            for source in self.sources_for_need(
                topic_plan.topic,
                need,
                sources,
            ):

                for candidate in self.list_for_source_need(
                    topic_plan.topic,
                    need,
                    source,
                ):
                    key = (
                        candidate.information_need,
                        candidate.url,
                    )

                    if key in seen_keys:
                        continue

                    seen_keys.add(key)
                    candidates.append(candidate)

        return candidates
