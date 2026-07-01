from datetime import datetime

from pydantic import BaseModel


class CriterionSchema(BaseModel):
    name: str
    description: str
    weight: float = 1.0


class RubricCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: list[CriterionSchema]


class RubricResponse(BaseModel):
    id: str
    name: str
    description: str | None
    criteria: list[CriterionSchema]
    created_at: datetime

    model_config = {"from_attributes": True}
