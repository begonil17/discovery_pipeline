from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class RawArticle(BaseModel):
    title: str
    text: str


class Nugget(BaseModel):
    nugget_id: str
    text: str
    importance: int = Field(ge=1, le=10)
    source_article: str
    detail_level: Optional[Literal["high", "medium", "low"]] = None


class NuggetList(BaseModel):
    nuggets: List[Nugget]


class RawQAPair(BaseModel):
    question: str
    answer: str
    source_article: str
    importance: int = Field(ge=1, le=10)
    storage_type: Literal["raw_qa"] = "raw_qa"


class RawQAList(BaseModel):
    qa_pairs: List[RawQAPair]


class FactLinkedQAPair(BaseModel):
    nugget_id: str
    question: str
    answer: str
    source_article: str
    storage_type: Literal["nugget_qa"] = "nugget_qa"


class FactLinkedQAList(BaseModel):
    qa_pairs: List[FactLinkedQAPair]

class StorageDecision(BaseModel):
    nugget_id: str
    action: Literal["keep_full", "keep_compressed", "merge", "skip"]
    final_text: str
    detail_level: Literal["high", "medium", "low"]
    questions_per_nugget: int = Field(ge=0, le=3)
    reason: str


class FactValidation(BaseModel):
    nugget_id: str
    verdict: Literal[
        "supported",
        "partially_supported",
        "unsupported"
    ]
    corrected_text: str
    reason: str

class TopicCandidate(BaseModel):
    title: str
    source_type: Literal["focus", "category_extra"]
    focus_point: Optional[str] = None
    coverage_score: int = Field(ge=1, le=10)
    reason: str


class TopicSelectionOutput(BaseModel):
    topics_by_category: dict[str, list[TopicCandidate]]


class QuestionParaphrase(BaseModel):
    direct: str
    conversational: str
    indirect: str


class QuestionParaphraseBatch(BaseModel):
    paraphrases: list[QuestionParaphrase]

