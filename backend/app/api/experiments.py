import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis
from app.schemas.experiment import ExperimentCreate, ExperimentListResponse, ExperimentOut, ExperimentUpdate
from app.schemas.task import FailureGroup, TaskListResponse, TaskOut
from app.schemas.report import ComparisonResult, FailureClusterOut
from app.services import experiment_service, task_service, cluster_service, report_service
from app.services.metric_service import get_metric_summary
from app.schemas.metric import MetricSummary

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    tags: Annotated[list[str], Query()] = [],
    db: AsyncSession = Depends(get_db),
):
    items, total = await experiment_service.list_experiments(db, page, limit, status, tags or None)
    return ExperimentListResponse(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=ExperimentOut, status_code=201)
async def create_experiment(data: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    return await experiment_service.create_experiment(db, data)


@router.get("/{experiment_id}", response_model=ExperimentOut)
async def get_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await experiment_service.get_experiment(db, experiment_id)


@router.patch("/{experiment_id}", response_model=ExperimentOut)
async def update_experiment(
    experiment_id: uuid.UUID, data: ExperimentUpdate, db: AsyncSession = Depends(get_db)
):
    return await experiment_service.update_experiment(db, experiment_id, data)


@router.delete("/{experiment_id}", status_code=204)
async def delete_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await experiment_service.delete_experiment(db, experiment_id)


@router.post("/{experiment_id}/run", response_model=ExperimentOut)
async def run_experiment(
    experiment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await experiment_service.run_experiment(db, redis, experiment_id)


@router.post("/{experiment_id}/cancel", response_model=ExperimentOut)
async def cancel_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await experiment_service.cancel_experiment(db, experiment_id)


@router.post("/{experiment_id}/clone", response_model=ExperimentOut, status_code=201)
async def clone_experiment(
    experiment_id: uuid.UUID,
    overrides: dict | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await experiment_service.clone_experiment(db, experiment_id, overrides)


@router.get("/{experiment_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    experiment_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = None,
    worker_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await task_service.list_tasks(db, experiment_id, page, limit, status, worker_id)
    return TaskListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{experiment_id}/metrics/summary", response_model=MetricSummary)
async def get_metrics_summary(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await get_metric_summary(db, experiment_id)


@router.get("/{experiment_id}/failures", response_model=list[FailureGroup])
async def get_failures(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await task_service.get_task_failures(db, experiment_id)


@router.get("/{experiment_id}/clusters", response_model=list[FailureClusterOut])
async def get_clusters(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    clusters = await cluster_service.get_clusters(db, experiment_id)
    if not clusters:
        clusters = await cluster_service.cluster_failures(db, experiment_id)
    return clusters


@router.get("/{baseline_id}/compare/{candidate_id}", response_model=ComparisonResult)
async def compare_experiments(
    baseline_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_comparison(db, baseline_id, candidate_id)
