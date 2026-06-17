import uuid
from datetime import datetime

from pydantic import BaseModel


class MetricOut(BaseModel):
    id: int
    task_id: uuid.UUID
    experiment_id: uuid.UUID
    name: str
    value: float
    unit: str | None
    computed_at: datetime

    model_config = {"from_attributes": True}


class MetricAggregate(BaseModel):
    name: str
    mean: float
    p50: float
    p95: float
    p99: float
    min: float
    max: float
    count: int
    unit: str | None


class MetricSummary(BaseModel):
    experiment_id: uuid.UUID
    metrics: list[MetricAggregate]


class MetricListResponse(BaseModel):
    items: list[MetricOut]
    total: int
    page: int
    limit: int
