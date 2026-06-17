import uuid
from datetime import datetime, timezone

import structlog
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.dataset import DatasetRow
from app.models.experiment import Experiment
from app.models.task import Task
from app.schemas.experiment import ExperimentCreate, ExperimentUpdate
from app.services import queue_service

log = structlog.get_logger()


async def create_experiment(db: AsyncSession, data: ExperimentCreate) -> Experiment:
    exp = Experiment(
        name=data.name,
        description=data.description,
        dataset_id=data.dataset_id,
        model_name=data.model_name,
        prompt_template=data.prompt_template,
        tags=data.tags,
        config=data.config,
        created_by=data.created_by,
        status="draft",
        version=1,
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    log.info("experiment_created", experiment_id=str(exp.id))
    return exp


async def get_experiment(db: AsyncSession, experiment_id: uuid.UUID) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise NotFoundError("Experiment", str(experiment_id))
    return exp


async def list_experiments(
    db: AsyncSession, page: int = 1, limit: int = 20, status: str | None = None, tags: list[str] | None = None
) -> tuple[list[Experiment], int]:
    offset = (page - 1) * limit
    q = select(Experiment)
    if status:
        q = q.where(Experiment.status == status)
    if tags:
        q = q.where(Experiment.tags.contains(tags))
    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()
    result = await db.execute(q.order_by(Experiment.created_at.desc()).offset(offset).limit(limit))
    return list(result.scalars()), total


async def update_experiment(
    db: AsyncSession, experiment_id: uuid.UUID, data: ExperimentUpdate
) -> Experiment:
    exp = await get_experiment(db, experiment_id)
    if exp.status != "draft":
        raise BadRequestError("Only draft experiments can be updated.")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(exp, field, val)
    await db.commit()
    await db.refresh(exp)
    return exp


async def run_experiment(db: AsyncSession, redis: Redis, experiment_id: uuid.UUID) -> Experiment:
    exp = await get_experiment(db, experiment_id)
    if exp.status not in ("draft", "failed"):
        raise BadRequestError(f"Cannot run experiment in '{exp.status}' status.")
    if not exp.dataset_id:
        raise BadRequestError("Experiment has no dataset assigned.")

    rows_result = await db.execute(
        select(DatasetRow).where(DatasetRow.dataset_id == exp.dataset_id).order_by(DatasetRow.row_index)
    )
    rows = list(rows_result.scalars())
    if not rows:
        raise BadRequestError("Dataset has no rows.")

    evaluator_type = exp.config.get("evaluator_type", "exact_match")
    payloads = [
        {
            "task_id": str(uuid.uuid4()),
            "experiment_id": str(exp.id),
            "dataset_row_id": row.id,
            "evaluator_type": evaluator_type,
            "config": {**exp.config, "model_name": exp.model_name, "prompt_template": exp.prompt_template},
            "input_data": row.input_data,
            "expected_output": row.expected,
            "attempt": 1,
            "max_attempts": exp.config.get("max_attempts", 3),
            "priority": 0,
        }
        for row in rows
    ]

    tasks = [
        Task(
            id=uuid.UUID(p["task_id"]),
            experiment_id=exp.id,
            dataset_row_id=p["dataset_row_id"],
            status="PENDING",
            max_attempts=p["max_attempts"],
            config_override=p["config"],
        )
        for p in payloads
    ]
    db.add_all(tasks)

    exp.status = "running"
    exp.started_at = datetime.now(timezone.utc)
    exp.total_tasks = len(payloads)
    exp.completed_tasks = 0
    exp.failed_tasks = 0

    await db.commit()

    await queue_service.init_experiment_progress(redis, str(exp.id), len(payloads))
    await queue_service.enqueue_tasks(redis, payloads)

    log.info("experiment_started", experiment_id=str(exp.id), tasks=len(payloads))
    return exp


async def cancel_experiment(db: AsyncSession, experiment_id: uuid.UUID) -> Experiment:
    exp = await get_experiment(db, experiment_id)
    if exp.status not in ("running", "draft"):
        raise BadRequestError(f"Cannot cancel experiment in '{exp.status}' status.")
    exp.status = "cancelled"
    await db.execute(
        Task.__table__.update()
        .where(Task.experiment_id == exp.id, Task.status == "PENDING")
        .values(status="FAILED", error_message="Experiment cancelled")
    )
    await db.commit()
    await db.refresh(exp)
    return exp


async def clone_experiment(
    db: AsyncSession, experiment_id: uuid.UUID, overrides: dict | None = None
) -> Experiment:
    source = await get_experiment(db, experiment_id)
    overrides = overrides or {}
    clone = Experiment(
        name=overrides.get("name", f"{source.name} (v{source.version + 1})"),
        description=overrides.get("description", source.description),
        version=source.version + 1,
        parent_id=source.id,
        config={**source.config, **overrides.get("config", {})},
        model_name=overrides.get("model_name", source.model_name),
        prompt_template=overrides.get("prompt_template", source.prompt_template),
        tags=overrides.get("tags", list(source.tags)),
        dataset_id=overrides.get("dataset_id", source.dataset_id),
        created_by=overrides.get("created_by", source.created_by),
        status="draft",
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    log.info("experiment_cloned", source_id=str(source.id), clone_id=str(clone.id))
    return clone


async def delete_experiment(db: AsyncSession, experiment_id: uuid.UUID) -> None:
    exp = await get_experiment(db, experiment_id)
    exp.status = "cancelled"
    await db.commit()


async def check_and_complete_experiment(db: AsyncSession, redis: Redis, experiment_id: uuid.UUID) -> None:
    progress = await queue_service.get_experiment_progress(redis, str(experiment_id))
    total = int(progress.get("total", 0))
    completed = int(progress.get("completed", 0))
    failed = int(progress.get("failed", 0))

    if total > 0 and (completed + failed) >= total:
        exp = await get_experiment(db, experiment_id)
        if exp.status == "running":
            exp.status = "completed" if failed == 0 else "failed"
            exp.completed_at = datetime.now(timezone.utc)
            exp.completed_tasks = completed
            exp.failed_tasks = failed
            await db.commit()
            log.info("experiment_completed", experiment_id=str(experiment_id), status=exp.status)
