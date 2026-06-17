import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.metric import MetricListResponse, MetricSummary
from app.services.metric_service import get_metric_summary, list_metrics, list_metric_names

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/names", response_model=list[str])
async def get_metric_names(db: AsyncSession = Depends(get_db)):
    return await list_metric_names(db)


@router.get("/experiments/{experiment_id}", response_model=MetricListResponse)
async def get_experiment_metrics(
    experiment_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_metrics(db, experiment_id, page, limit)
    return MetricListResponse(items=items, total=total, page=page, limit=limit)
