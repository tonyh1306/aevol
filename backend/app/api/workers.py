import uuid

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis
from app.schemas.worker import WorkerHeartbeat, WorkerListResponse, WorkerOut, WorkerRegister
from app.services import worker_service

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get("", response_model=WorkerListResponse)
async def list_workers(db: AsyncSession = Depends(get_db)):
    items = await worker_service.list_workers(db)
    return WorkerListResponse(items=items, total=len(items))


@router.post("/register", response_model=WorkerOut, status_code=201)
async def register_worker(
    data: WorkerRegister,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await worker_service.register_worker(db, redis, data)


@router.get("/{worker_id}", response_model=WorkerOut)
async def get_worker(worker_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await worker_service.get_worker(db, worker_id)


@router.post("/{worker_id}/heartbeat", response_model=WorkerOut)
async def heartbeat(
    worker_id: uuid.UUID,
    data: WorkerHeartbeat,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await worker_service.update_heartbeat(db, redis, worker_id, data)


@router.delete("/{worker_id}", status_code=204)
async def deregister_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    await worker_service.deregister_worker(db, redis, worker_id)
