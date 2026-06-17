import uuid
from datetime import datetime

from pydantic import BaseModel


class WorkerRegister(BaseModel):
    hostname: str
    pid: int
    version: str | None = None
    capabilities: list[str] = []


class WorkerHeartbeat(BaseModel):
    status: str
    current_task_id: uuid.UUID | None = None
    cpu_percent: float | None = None
    memory_mb: int | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0


class WorkerOut(BaseModel):
    id: uuid.UUID
    hostname: str
    pid: int
    version: str | None
    status: str
    current_task_id: uuid.UUID | None
    tasks_completed: int
    tasks_failed: int
    last_heartbeat: datetime
    registered_at: datetime
    cpu_percent: float | None
    memory_mb: int | None
    capabilities: list[str]

    model_config = {"from_attributes": True}


class WorkerListResponse(BaseModel):
    items: list[WorkerOut]
    total: int
