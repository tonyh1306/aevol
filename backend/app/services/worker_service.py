import json
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError
from app.models.worker import Worker
from app.models.task import Task
from app.schemas.worker import WorkerHeartbeat, WorkerRegister

log = structlog.get_logger()


async def register_worker(db: AsyncSession, redis: Redis, data: WorkerRegister) -> Worker:
    worker = Worker(
        hostname=data.hostname,
        pid=data.pid,
        version=data.version,
        capabilities=data.capabilities,
        status="idle",
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    snapshot = {"worker_id": str(worker.id), "status": "idle", "heartbeat_at": datetime.now(timezone.utc).isoformat()}
    await redis.hset("eval:workers", str(worker.id), json.dumps(snapshot))
    log.info("worker_registered", worker_id=str(worker.id), hostname=data.hostname)
    return worker


async def update_heartbeat(
    db: AsyncSession, redis: Redis, worker_id: uuid.UUID, data: WorkerHeartbeat
) -> Worker:
    worker = await get_worker(db, worker_id)
    worker.status = data.status
    worker.current_task_id = data.current_task_id
    worker.cpu_percent = data.cpu_percent
    worker.memory_mb = data.memory_mb
    worker.tasks_completed = data.tasks_completed
    worker.tasks_failed = data.tasks_failed
    worker.last_heartbeat = datetime.now(timezone.utc)
    await db.commit()

    snapshot = {
        "worker_id": str(worker_id),
        "status": data.status,
        "current_task_id": str(data.current_task_id) if data.current_task_id else None,
        "cpu_percent": data.cpu_percent,
        "memory_mb": data.memory_mb,
        "tasks_completed": data.tasks_completed,
        "tasks_failed": data.tasks_failed,
        "heartbeat_at": worker.last_heartbeat.isoformat(),
    }
    await redis.hset("eval:workers", str(worker_id), json.dumps(snapshot))
    return worker


async def get_worker(db: AsyncSession, worker_id: uuid.UUID) -> Worker:
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    w = result.scalar_one_or_none()
    if not w:
        raise NotFoundError("Worker", str(worker_id))
    return w


async def list_workers(db: AsyncSession) -> list[Worker]:
    result = await db.execute(select(Worker).order_by(Worker.registered_at.desc()))
    return list(result.scalars())


async def deregister_worker(db: AsyncSession, redis: Redis, worker_id: uuid.UUID) -> None:
    worker = await get_worker(db, worker_id)
    worker.status = "dead"
    await db.commit()
    await redis.hdel("eval:workers", str(worker_id))
    log.info("worker_deregistered", worker_id=str(worker_id))


async def detect_dead_workers(db: AsyncSession) -> list[Worker]:
    threshold = datetime.now(timezone.utc) - timedelta(seconds=settings.WORKER_DEAD_THRESHOLD)
    result = await db.execute(
        select(Worker).where(
            Worker.status.in_(["idle", "busy"]),
            Worker.last_heartbeat < threshold,
        )
    )
    dead_workers = list(result.scalars())
    for worker in dead_workers:
        worker.status = "dead"
        if worker.current_task_id:
            task_res = await db.execute(select(Task).where(Task.id == worker.current_task_id))
            task = task_res.scalar_one_or_none()
            if task and task.status == "RUNNING":
                task.status = "PENDING"
                task.worker_id = None
                task.claimed_at = None
                log.warning("task_reclaimed", task_id=str(task.id), dead_worker=str(worker.id))
    if dead_workers:
        await db.commit()
        log.warning("workers_marked_dead", count=len(dead_workers))
    return dead_workers
