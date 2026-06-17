import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.agent_trace import AgentTrace
from app.models.metric import Metric
from app.models.task import Task
from app.schemas.task import AgentTraceStepOut, TaskOut
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskResultUpdate(BaseModel):
    status: str | None = None
    worker_id: uuid.UUID | None = None
    output_data: dict | None = None
    error_message: str | None = None
    error_type: str | None = None
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None


class MetricPayload(BaseModel):
    name: str
    value: float
    unit: str | None = None


class MetricsBatchBody(BaseModel):
    experiment_id: uuid.UUID
    metrics: list[MetricPayload]


class TraceStep(BaseModel):
    step_index: int
    step_type: str
    input_data: dict | None = None
    output_data: dict | None = None
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_result: dict | None = None
    latency_ms: int | None = None
    tokens_used: int | None = None
    error: str | None = None


class TracesBatchBody(BaseModel):
    steps: list[TraceStep]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await task_service.get_task(db, task_id)


@router.get("/{task_id}/trace", response_model=list[AgentTraceStepOut])
async def get_task_trace(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await task_service.get_task_trace(db, task_id)


@router.post("/{task_id}/retry", response_model=TaskOut)
async def retry_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task", str(task_id))
    if task.status not in ("FAILED", "DEAD"):
        raise BadRequestError(f"Task in status '{task.status}' cannot be retried.")
    task.status = "PENDING"
    task.attempt_count = 0
    task.error_message = None
    task.error_type = None
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}/result", response_model=TaskOut)
async def update_task_result(
    task_id: uuid.UUID, body: TaskResultUpdate, db: AsyncSession = Depends(get_db)
):
    """Called by workers to push task execution results."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task", str(task_id))

    if body.status:
        task.status = body.status
    if body.worker_id:
        task.worker_id = body.worker_id
    if body.output_data is not None:
        task.output_data = body.output_data
    if body.error_message is not None:
        task.error_message = body.error_message
    if body.error_type is not None:
        task.error_type = body.error_type
    if body.latency_ms is not None:
        task.latency_ms = body.latency_ms
    if body.prompt_tokens is not None:
        task.prompt_tokens = body.prompt_tokens
    if body.completion_tokens is not None:
        task.completion_tokens = body.completion_tokens
    if body.cost_usd is not None:
        task.cost_usd = Decimal(str(body.cost_usd))

    if body.status in ("COMPLETED", "FAILED", "DEAD"):
        task.completed_at = datetime.now(timezone.utc)
    if body.status == "RUNNING" and not task.claimed_at:
        task.claimed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/metrics", status_code=204)
async def push_task_metrics(
    task_id: uuid.UUID, body: MetricsBatchBody, db: AsyncSession = Depends(get_db)
):
    """Called by workers to push per-task evaluation metrics."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("Task", str(task_id))

    metric_rows = [
        Metric(
            task_id=task_id,
            experiment_id=body.experiment_id,
            name=m.name,
            value=m.value,
            unit=m.unit,
        )
        for m in body.metrics
    ]
    db.add_all(metric_rows)
    await db.commit()


@router.post("/{task_id}/traces", status_code=204)
async def push_task_traces(
    task_id: uuid.UUID, body: TracesBatchBody, db: AsyncSession = Depends(get_db)
):
    """Called by workers to persist agent execution trace steps."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("Task", str(task_id))

    trace_rows = [
        AgentTrace(
            task_id=task_id,
            step_index=s.step_index,
            step_type=s.step_type,
            input_data=s.input_data,
            output_data=s.output_data,
            tool_name=s.tool_name,
            tool_args=s.tool_args,
            tool_result=s.tool_result,
            latency_ms=s.latency_ms,
            tokens_used=s.tokens_used,
            error=s.error,
        )
        for s in body.steps
    ]
    db.add_all(trace_rows)
    await db.commit()
