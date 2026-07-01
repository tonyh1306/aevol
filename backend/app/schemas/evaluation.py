from datetime import datetime

from pydantic import BaseModel


class CriterionScoreSchema(BaseModel):
    criterion: str
    score: float
    reasoning: str


class EvaluationResponse(BaseModel):
    id: str
    run_id: str
    trace_id: str
    scores: list[CriterionScoreSchema] | None
    overall_score: float | None
    passed: bool | None
    reasoning: str | None
    error: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
