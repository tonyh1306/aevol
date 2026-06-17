import uuid
from datetime import datetime

from pydantic import BaseModel


class ExperimentCreate(BaseModel):
    name: str
    description: str | None = None
    dataset_id: uuid.UUID | None = None
    model_name: str | None = None
    prompt_template: str | None = None
    tags: list[str] = []
    config: dict = {}
    created_by: str | None = None


class ExperimentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    model_name: str | None = None
    prompt_template: str | None = None
    tags: list[str] | None = None
    config: dict | None = None


class ExperimentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    version: int
    parent_id: uuid.UUID | None
    config: dict
    model_name: str | None
    prompt_template: str | None
    tags: list[str]
    status: str
    dataset_id: uuid.UUID | None
    created_by: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    total_tasks: int
    completed_tasks: int
    failed_tasks: int

    model_config = {"from_attributes": True}


class ExperimentListResponse(BaseModel):
    items: list[ExperimentOut]
    total: int
    page: int
    limit: int


class ExperimentProgress(BaseModel):
    experiment_id: uuid.UUID
    total: int
    completed: int
    failed: int
    pending: int
    running: int
    progress_pct: float
