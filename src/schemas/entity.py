from pydantic import BaseModel, Field
from src.planner.schemas import PlannerDecision
from src.search.schemas import SearchPlan
from src.fetcher.schemas import Document

class Entity(BaseModel):

    # Identity
    title: str
    url: str
    source: str = "Wikipedia"

    # Discovery
    depth: int
    parent: str | None = None
    children: list[str] = Field(default_factory=list)

    # Wikipedia metadata
    summary: str = ""
    categories: list[str] = Field(default_factory=list)

    # Future fields
    entity_type: str | None = None
    importance: float | None = None

    planner: PlannerDecision | None = None

    search_plan: SearchPlan | None = None

    documents: list[Document] = []