import csv
import io
import json
import os
import uuid
from pathlib import Path
from typing import Any

import aiofiles
import structlog
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.dataset import Dataset, DatasetRow

log = structlog.get_logger()

ALLOWED_FORMATS = {"csv", "jsonl"}


async def upload_dataset(db: AsyncSession, file: UploadFile, name: str, description: str | None) -> Dataset:
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in ALLOWED_FORMATS:
        raise BadRequestError(f"Unsupported format '{ext}'. Must be csv or jsonl.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = uuid.uuid4()
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.{ext}")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise BadRequestError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    rows, schema_info = _parse_content(content.decode("utf-8"), ext)

    dataset = Dataset(
        name=name,
        description=description,
        format=ext,
        row_count=len(rows),
        file_path=file_path,
        file_size=len(content),
        schema_info=schema_info,
    )
    db.add(dataset)
    await db.flush()

    db_rows = [
        DatasetRow(
            dataset_id=dataset.id,
            row_index=i,
            input_data=row,
            expected=row.pop("expected", None) if isinstance(row, dict) else None,
        )
        for i, row in enumerate(rows)
    ]
    db.add_all(db_rows)
    await db.commit()
    await db.refresh(dataset)
    log.info("dataset_uploaded", dataset_id=str(dataset.id), rows=len(rows))
    return dataset


def _parse_content(text: str, fmt: str) -> tuple[list[dict[str, Any]], dict]:
    rows: list[dict[str, Any]] = []
    if fmt == "csv":
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(r) for r in reader]
        schema_info = {"columns": list(rows[0].keys()) if rows else [], "format": "csv"}
    else:
        for line in text.strip().splitlines():
            if line.strip():
                rows.append(json.loads(line))
        schema_info = {"columns": list(rows[0].keys()) if rows else [], "format": "jsonl"}
    return rows, schema_info


async def get_dataset(db: AsyncSession, dataset_id: uuid.UUID) -> Dataset:
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise NotFoundError("Dataset", str(dataset_id))
    return ds


async def list_datasets(db: AsyncSession, page: int = 1, limit: int = 20) -> tuple[list[Dataset], int]:
    offset = (page - 1) * limit
    total_res = await db.execute(select(func.count()).select_from(Dataset))
    total = total_res.scalar_one()
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()).offset(offset).limit(limit))
    return list(result.scalars()), total


async def list_dataset_rows(
    db: AsyncSession, dataset_id: uuid.UUID, page: int = 1, limit: int = 50
) -> tuple[list[DatasetRow], int]:
    await get_dataset(db, dataset_id)
    offset = (page - 1) * limit
    total_res = await db.execute(
        select(func.count()).select_from(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
    )
    total = total_res.scalar_one()
    result = await db.execute(
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset_id)
        .order_by(DatasetRow.row_index)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars()), total


async def delete_dataset(db: AsyncSession, dataset_id: uuid.UUID) -> None:
    ds = await get_dataset(db, dataset_id)
    await db.delete(ds)
    await db.commit()
    if os.path.exists(ds.file_path):
        os.unlink(ds.file_path)
