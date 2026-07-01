from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.rubric import RubricCreate, RubricResponse
from app.services import rubric_service

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.post("", response_model=RubricResponse, status_code=201)
async def create_rubric(data: RubricCreate, db: AsyncSession = Depends(get_db)):
    return await rubric_service.create_rubric(db, data)


@router.get("", response_model=list[RubricResponse])
async def list_rubrics(db: AsyncSession = Depends(get_db)):
    return await rubric_service.list_rubrics(db)


@router.get("/{rubric_id}", response_model=RubricResponse)
async def get_rubric(rubric_id: str, db: AsyncSession = Depends(get_db)):
    rubric = await rubric_service.get_rubric(db, rubric_id)
    if not rubric:
        raise HTTPException(404, "rubric not found")
    return rubric
