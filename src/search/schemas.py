from pydantic import BaseModel


class SearchResult(BaseModel):

    url: str

    title: str

    score: float | None = None

    reason: str


class SearchTask(BaseModel):

    information: str

    query: str

    results: list[SearchResult] = []


class SearchPlan(BaseModel):

    tasks: list[SearchTask]