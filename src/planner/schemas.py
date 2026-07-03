from pydantic import BaseModel, Field


class EntityType(BaseModel):
    """
    Standardized entity type assigned by the planner.
    """

    name: str = Field(
        description="Broad standardized entity type."
    )

    subtype: str | None = Field(
        default=None,
        description="Optional subtype of the entity."
    )


class InformationItem(BaseModel):
    """
    One piece of information that should later be collected.
    """

    name: str = Field(
        description="Standardized information type."
    )

    priority: int = Field(
        ge=1,
        le=5,
        description="Priority from 1 (lowest) to 5 (highest)."
    )


class PlannerDecision(BaseModel):
    """
    Complete planning decision for one discovered entity.
    """

    include: bool = Field(
        description=(
            "Whether the entity should become part "
            "of the knowledge base."
        )
    )

    expand: bool = Field(
        description=(
            "Whether Wikipedia discovery should continue "
            "from this entity."
        )
    )

    entity_type: EntityType

    information_to_collect: list[InformationItem] = Field(
        default_factory=list
    )

    reason: str = Field(
        description="Short explanation of the decision."
    )