from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.evaluation import EvaluationResponse
from app.schemas.run import RunCreate, RunResponse
from app.services import run_service

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(data: RunCreate, db: AsyncSession = Depends(get_db)):
    return await run_service.create_run(db, data)


@router.get("", response_model=list[RunResponse])
async def list_runs(db: AsyncSession = Depends(get_db)):
    return await run_service.list_runs(db)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await run_service.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@router.get("/{run_id}/evaluations", response_model=list[EvaluationResponse])
async def get_run_evaluations(run_id: str, db: AsyncSession = Depends(get_db)):
    return await run_service.get_run_evaluations(db, run_id)
