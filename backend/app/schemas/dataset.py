import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DatasetBase(BaseModel):
    name: str
    description: str | None = None
    format: str  # csv | jsonl


class DatasetCreate(DatasetBase):
    pass


class DatasetOut(DatasetBase):
    id: uuid.UUID
    row_count: int | None
    file_size: int | None
    schema_info: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetRowOut(BaseModel):
    id: int
    dataset_id: uuid.UUID
    row_index: int
    input_data: dict[str, Any]
    expected: dict | None

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    items: list[DatasetOut]
    total: int
    page: int
    limit: int


class DatasetRowsResponse(BaseModel):
    items: list[DatasetRowOut]
    total: int
    page: int
    limit: int
