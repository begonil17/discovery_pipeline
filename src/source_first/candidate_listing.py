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
        max_results_per_source_need: int = 10,
    ):
        self.tavily = tavily
        self.max_results_per_source_need = max_results_per_source_need

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

        candidates = []
        seen_urls = set()

        for query in self.build_queries(
            topic,
            need,
            source,
        ):
            response = self._tavily_client().search(
                query=query,
                max_results=min(
                    self.max_results_per_source_need,
                    source.collection_strategy.max_candidates,
                ),
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

    def list_candidates(
        self,
        topic_plan: TopicPlan,
        sources: list[SourceProfile],
    ) -> list[CandidateItem]:
        candidates = []
        seen_keys = set()

        for need in topic_plan.information_needs:
            for source in sources:
                if not source.supports_need(
                    topic_plan.topic,
                    need.name,
                ):
                    continue

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
