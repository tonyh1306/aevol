import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.models.report import Report
from app.schemas.report import RegressionFlag, ReportCreate
from app.services.metric_service import get_metric_summary
from app.services.experiment_service import get_experiment

log = structlog.get_logger()

METRIC_DIRECTION = {
    "accuracy": "higher_is_better",
    "bleu": "higher_is_better",
    "rouge": "higher_is_better",
    "pass_at_k": "higher_is_better",
    "latency_ms": "lower_is_better",
    "cost_usd": "lower_is_better",
    "failure_rate": "lower_is_better",
    "tokens": "lower_is_better",
}


async def generate_report(db: AsyncSession, data: ReportCreate) -> Report:
    baseline = await get_experiment(db, data.baseline_id)
    candidate = await get_experiment(db, data.candidate_id)

    if baseline.status not in ("completed", "failed") or candidate.status not in ("completed", "failed"):
        raise BadRequestError("Both experiments must be completed before generating a report.")

    baseline_summary = await get_metric_summary(db, data.baseline_id)
    candidate_summary = await get_metric_summary(db, data.candidate_id)

    baseline_map = {m.name: m for m in baseline_summary.metrics}
    candidate_map = {m.name: m for m in candidate_summary.metrics}

    common_names = set(baseline_map) & set(candidate_map)
    deltas = []
    regressions: list[RegressionFlag] = []
    improvements = []
    stable = []

    for name in common_names:
        b = baseline_map[name].mean
        c = candidate_map[name].mean
        if b == 0:
            delta_pct = 0.0
        else:
            delta_pct = ((c - b) / abs(b)) * 100

        direction = METRIC_DIRECTION.get(name, "higher_is_better")
        is_regression = (direction == "higher_is_better" and delta_pct < -5.0) or \
                        (direction == "lower_is_better" and delta_pct > 5.0)
        is_improvement = (direction == "higher_is_better" and delta_pct > 5.0) or \
                         (direction == "lower_is_better" and delta_pct < -5.0)

        deltas.append({"metric": name, "baseline": b, "candidate": c, "delta_pct": round(delta_pct, 2)})

        if is_regression:
            severity = "critical" if abs(delta_pct) > 20 else "warning"
            regressions.append(RegressionFlag(
                metric=name, baseline_value=b, candidate_value=c, delta_pct=round(delta_pct, 2), severity=severity
            ))
        elif is_improvement:
            improvements.append(name)
        else:
            stable.append(name)

    title = data.title or f"Report: {baseline.name} vs {candidate.name}"
    report = Report(
        title=title,
        baseline_id=data.baseline_id,
        candidate_id=data.candidate_id,
        summary={
            "deltas": deltas,
            "improvements": improvements,
            "stable": stable,
            "regression_count": len(regressions),
        },
        regression_flags=[r.model_dump() for r in regressions],
        generated_at=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    log.info("report_generated", report_id=str(report.id), regressions=len(regressions))
    return report


async def get_report(db: AsyncSession, report_id: uuid.UUID) -> Report:
    from sqlalchemy import select
    from app.core.exceptions import NotFoundError
    result = await db.execute(select(Report).where(Report.id == report_id))
    r = result.scalar_one_or_none()
    if not r:
        raise NotFoundError("Report", str(report_id))
    return r


async def list_reports(db: AsyncSession) -> tuple[list[Report], int]:
    from sqlalchemy import select, func
    total_res = await db.execute(select(func.count()).select_from(Report))
    total = total_res.scalar_one()
    result = await db.execute(select(Report).order_by(Report.generated_at.desc()))
    return list(result.scalars()), total


async def get_comparison(db: AsyncSession, baseline_id: uuid.UUID, candidate_id: uuid.UUID) -> dict:
    baseline_summary = await get_metric_summary(db, baseline_id)
    candidate_summary = await get_metric_summary(db, candidate_id)

    baseline_map = {m.name: m.mean for m in baseline_summary.metrics}
    candidate_map = {m.name: m.mean for m in candidate_summary.metrics}
    common = set(baseline_map) & set(candidate_map)

    deltas = []
    regressions: list[RegressionFlag] = []
    for name in common:
        b = baseline_map[name]
        c = candidate_map[name]
        delta_pct = ((c - b) / abs(b)) * 100 if b != 0 else 0.0
        deltas.append({"metric": name, "baseline": b, "candidate": c, "delta_pct": round(delta_pct, 2)})
        direction = METRIC_DIRECTION.get(name, "higher_is_better")
        is_regression = (direction == "higher_is_better" and delta_pct < -5.0) or \
                        (direction == "lower_is_better" and delta_pct > 5.0)
        if is_regression:
            severity = "critical" if abs(delta_pct) > 20 else "warning"
            regressions.append(RegressionFlag(
                metric=name, baseline_value=b, candidate_value=c,
                delta_pct=round(delta_pct, 2), severity=severity
            ))

    return {
        "baseline_id": str(baseline_id),
        "candidate_id": str(candidate_id),
        "baseline_metrics": [m.model_dump() for m in baseline_summary.metrics],
        "candidate_metrics": [m.model_dump() for m in candidate_summary.metrics],
        "deltas": deltas,
        "regressions": [r.model_dump() for r in regressions],
    }
