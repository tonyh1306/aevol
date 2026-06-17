import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TaskOut(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    dataset_row_id: int | None
    status: str
    priority: int
    attempt_count: int
    max_attempts: int
    worker_id: uuid.UUID | None
    enqueued_at: datetime
    claimed_at: datetime | None
    completed_at: datetime | None
    output_data: dict | None
    error_message: str | None
    error_type: str | None
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: Decimal | None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    limit: int


class FailureGroup(BaseModel):
    error_type: str | None
    count: int
    sample_messages: list[str]


class AgentTraceStepOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    step_index: int
    step_type: str
    input_data: dict | None
    output_data: dict | None
    tool_name: str | None
    tool_args: dict | None
    tool_result: dict | None
    latency_ms: int | None
    tokens_used: int | None
    error: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}
