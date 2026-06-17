import uuid

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import Metric
from app.schemas.metric import MetricAggregate, MetricSummary


async def list_metrics(
    db: AsyncSession, experiment_id: uuid.UUID, page: int = 1, limit: int = 200
) -> tuple[list[Metric], int]:
    offset = (page - 1) * limit
    total_res = await db.execute(
        select(func.count()).select_from(Metric).where(Metric.experiment_id == experiment_id)
    )
    total = total_res.scalar_one()
    result = await db.execute(
        select(Metric)
        .where(Metric.experiment_id == experiment_id)
        .order_by(Metric.computed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars()), total


async def get_metric_summary(db: AsyncSession, experiment_id: uuid.UUID) -> MetricSummary:
    name_res = await db.execute(
        select(Metric.name).where(Metric.experiment_id == experiment_id).distinct()
    )
    metric_names = [r[0] for r in name_res]

    aggregates: list[MetricAggregate] = []
    for name in metric_names:
        values_res = await db.execute(
            select(Metric.value, Metric.unit)
            .where(Metric.experiment_id == experiment_id, Metric.name == name)
        )
        rows = values_res.fetchall()
        if not rows:
            continue
        values = np.array([r[0] for r in rows])
        unit = rows[0][1]
        aggregates.append(
            MetricAggregate(
                name=name,
                mean=float(np.mean(values)),
                p50=float(np.percentile(values, 50)),
                p95=float(np.percentile(values, 95)),
                p99=float(np.percentile(values, 99)),
                min=float(np.min(values)),
                max=float(np.max(values)),
                count=len(values),
                unit=unit,
            )
        )

    return MetricSummary(experiment_id=experiment_id, metrics=aggregates)


async def get_aggregate_by_name(db: AsyncSession, experiment_id: uuid.UUID, name: str) -> dict:
    values_res = await db.execute(
        select(Metric.value).where(Metric.experiment_id == experiment_id, Metric.name == name)
    )
    values = np.array([r[0] for r in values_res])
    if len(values) == 0:
        return {}
    return {
        "name": name,
        "mean": float(np.mean(values)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "count": len(values),
    }


async def list_metric_names(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Metric.name).distinct())
    return [r[0] for r in result]
