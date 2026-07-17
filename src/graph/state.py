from typing import TypedDict

from src.schemas.seed import Seed
from src.schemas.entity import Entity


class DiscoveryState(TypedDict, total=False):

    seed: Seed

    discovered_entities: list[Entity]

    frontier: list[Entity]

    rejected_entities: list[Entity]

    errors: list[str]

    refresh_discovery: bool

    refresh_enrichment: bool

    refresh_planner: bool

    refresh_search: bool

    refresh_fetch: bool
