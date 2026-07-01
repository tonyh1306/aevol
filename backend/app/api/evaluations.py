from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.evaluation import Evaluation
from app.services.run_service import mark_evaluation_done, mark_evaluation_failed

router = APIRouter(prefix="/runs", tags=["evaluations"])


class EvaluationPatch(BaseModel):
    scores: list | None = None
    overall_score: float | None = None
    passed: bool | None = None
    reasoning: str | None = None
    error: str | None = None
    status: str


@router.patch("/{run_id}/evaluations/{evaluation_id}")
async def patch_evaluation(
    run_id: str,
    evaluation_id: str,
    data: EvaluationPatch,
    db: AsyncSession = Depends(get_db),
):
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation or evaluation.run_id != run_id:
        raise HTTPException(404, "evaluation not found")

    if data.status == "completed" and data.scores is not None:
        await mark_evaluation_done(
            db,
            evaluation_id,
            data.scores,
            data.overall_score or 0.0,
            data.passed or False,
            data.reasoning or "",
        )
    elif data.status == "failed":
        await mark_evaluation_failed(db, evaluation_id, data.error or "unknown error")

    return {"ok": True}
