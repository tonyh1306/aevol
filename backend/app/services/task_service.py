import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.agent_trace import AgentTrace
from app.models.task import Task
from app.schemas.task import FailureGroup


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("Task", str(task_id))
    return task


async def list_tasks(
    db: AsyncSession,
    experiment_id: uuid.UUID,
    page: int = 1,
    limit: int = 50,
    status: str | None = None,
    worker_id: uuid.UUID | None = None,
) -> tuple[list[Task], int]:
    offset = (page - 1) * limit
    q = select(Task).where(Task.experiment_id == experiment_id)
    if status:
        q = q.where(Task.status == status)
    if worker_id:
        q = q.where(Task.worker_id == worker_id)
    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()
    result = await db.execute(q.order_by(Task.enqueued_at.asc()).offset(offset).limit(limit))
    return list(result.scalars()), total


async def get_task_failures(db: AsyncSession, experiment_id: uuid.UUID) -> list[FailureGroup]:
    result = await db.execute(
        select(Task.error_type, func.count().label("count"))
        .where(Task.experiment_id == experiment_id, Task.status.in_(["FAILED", "DEAD"]))
        .group_by(Task.error_type)
        .order_by(text("count DESC"))
    )
    rows = result.fetchall()

    groups = []
    for error_type, count in rows:
        sample_result = await db.execute(
            select(Task.error_message)
            .where(Task.experiment_id == experiment_id, Task.error_type == error_type)
            .limit(3)
        )
        samples = [r[0] for r in sample_result if r[0]]
        groups.append(FailureGroup(error_type=error_type, count=count, sample_messages=samples))
    return groups


async def get_task_trace(db: AsyncSession, task_id: uuid.UUID) -> list[AgentTrace]:
    await get_task(db, task_id)
    result = await db.execute(
        select(AgentTrace)
        .where(AgentTrace.task_id == task_id)
        .order_by(AgentTrace.step_index)
    )
    return list(result.scalars())
