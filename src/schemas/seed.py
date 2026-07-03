from pydantic import BaseModel

from pydantic import BaseModel

from src.config.settings import (
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_DEPTH,
    DEFAULT_ENTITY_LIMIT,
)


class Seed(BaseModel):

    title: str

    language: str = DEFAULT_LANGUAGE

    max_depth: int = DEFAULT_MAX_DEPTH

    entity_limit: int = DEFAULT_ENTITY_LIMIT
