import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportCreate(BaseModel):
    baseline_id: uuid.UUID
    candidate_id: uuid.UUID
    title: str | None = None


class RegressionFlag(BaseModel):
    metric: str
    baseline_value: float
    candidate_value: float
    delta_pct: float
    severity: str  # warning | critical


class ReportOut(BaseModel):
    id: uuid.UUID
    title: str
    baseline_id: uuid.UUID
    candidate_id: uuid.UUID
    summary: dict
    regression_flags: list[RegressionFlag]
    generated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportOut]
    total: int


class ComparisonResult(BaseModel):
    baseline_id: uuid.UUID
    candidate_id: uuid.UUID
    baseline_metrics: list[dict]
    candidate_metrics: list[dict]
    deltas: list[dict]
    regressions: list[RegressionFlag]


class FailureClusterOut(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    cluster_label: str
    error_pattern: str
    sample_errors: list[str]
    task_count: int
    suggestion: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
