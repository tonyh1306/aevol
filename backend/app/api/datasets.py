import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.dataset import DatasetListResponse, DatasetOut, DatasetRowsResponse
from app.services import dataset_service

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await dataset_service.list_datasets(db, page, limit)
    return DatasetListResponse(items=items, total=total, page=page, limit=limit)


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    file: UploadFile,
    name: str = Form(...),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    return await dataset_service.upload_dataset(db, file, name, description)


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await dataset_service.get_dataset(db, dataset_id)


@router.get("/{dataset_id}/rows", response_model=DatasetRowsResponse)
async def list_rows(
    dataset_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await dataset_service.list_dataset_rows(db, dataset_id, page, limit)
    return DatasetRowsResponse(items=items, total=total, page=page, limit=limit)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await dataset_service.delete_dataset(db, dataset_id)
