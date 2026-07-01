import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.run import Run
from app.redis_client import get_redis
from app.schemas.run import RunCreate


async def create_run(db: AsyncSession, data: RunCreate) -> Run:
    run_id = str(uuid.uuid4())
    run = Run(
        id=run_id,
        name=data.name,
        rubric_id=data.rubric_id,
        judge_config=data.judge_config.model_dump(),
        status="pending",
        total=len(data.trace_ids),
    )
    db.add(run)

    for trace_id in data.trace_ids:
        db.add(Evaluation(
            id=str(uuid.uuid4()),
            run_id=run_id,
            trace_id=trace_id,
            status="pending",
        ))

    await db.commit()
    await db.refresh(run)
    await _enqueue_run(run_id, data)
    return run


async def get_run(db: AsyncSession, run_id: str) -> Run | None:
    return await db.get(Run, run_id)


async def list_runs(db: AsyncSession) -> list[Run]:
    result = await db.execute(select(Run).order_by(Run.created_at.desc()))
    return list(result.scalars().all())


async def get_run_evaluations(db: AsyncSession, run_id: str) -> list[Evaluation]:
    result = await db.execute(
        select(Evaluation).where(Evaluation.run_id == run_id).order_by(Evaluation.created_at)
    )
    return list(result.scalars().all())


async def mark_evaluation_done(
    db: AsyncSession,
    evaluation_id: str,
    scores: list,
    overall_score: float,
    passed: bool,
    reasoning: str,
) -> None:
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation:
        return
    evaluation.scores = scores
    evaluation.overall_score = overall_score
    evaluation.passed = passed
    evaluation.reasoning = reasoning
    evaluation.status = "completed"

    run = await db.get(Run, evaluation.run_id)
    if run:
        run.completed += 1
        if run.completed + run.failed >= run.total:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await _publish_event(evaluation.run_id, "evaluation_completed", {
        "evaluation_id": evaluation_id,
        "trace_id": evaluation.trace_id,
        "overall_score": overall_score,
        "passed": passed,
    })


async def mark_evaluation_failed(db: AsyncSession, evaluation_id: str, error: str) -> None:
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation:
        return
    evaluation.error = error
    evaluation.status = "failed"

    run = await db.get(Run, evaluation.run_id)
    if run:
        run.failed += 1
        if run.completed + run.failed >= run.total:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await _publish_event(evaluation.run_id, "evaluation_failed", {
        "evaluation_id": evaluation_id,
        "error": error,
    })


async def _enqueue_run(run_id: str, data: RunCreate) -> None:
    redis = get_redis()
    payload = json.dumps({
        "run_id": run_id,
        "rubric_id": data.rubric_id,
        "trace_ids": data.trace_ids,
        "judge_config": data.judge_config.model_dump(),
    })
    await redis.lpush("agentjudge:runs", payload)


async def _publish_event(run_id: str, event: str, data: dict) -> None:
    try:
        redis = get_redis()
        payload = json.dumps({"event": event, "run_id": run_id, "data": data})
        await redis.publish("agentjudge:sse", payload)
    except Exception:
        pass
