from typing import TypedDict

from src.schemas.seed import Seed
from src.schemas.entity import Entity


class DiscoveryState(TypedDict):

    seed: Seed

    discovered_entities: list[Entity]

    frontier: list[Entity]

    rejected_entities: list[Entity]

    errors: list[str]