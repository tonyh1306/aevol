import asyncio
import json
import os
from datetime import datetime, timezone

import psutil
import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings

log = structlog.get_logger()

_current_task_id: str | None = None
_worker_status: str = "idle"
_tasks_completed: int = 0
_tasks_failed: int = 0


def set_current_task(task_id: str | None) -> None:
    global _current_task_id, _worker_status
    _current_task_id = task_id
    _worker_status = "busy" if task_id else "idle"


def record_completed() -> None:
    global _tasks_completed
    _tasks_completed += 1


def record_failed() -> None:
    global _tasks_failed
    _tasks_failed += 1


async def heartbeat_loop(
    redis: Redis,
    http_client: httpx.AsyncClient,
    worker_id: str,
    shutdown_event: asyncio.Event,
) -> None:
    proc = psutil.Process(os.getpid())
    while not shutdown_event.is_set():
        try:
            snapshot = {
                "worker_id": worker_id,
                "status": _worker_status,
                "current_task_id": _current_task_id,
                "cpu_percent": psutil.cpu_percent(),
                "memory_mb": proc.memory_info().rss // (1024 * 1024),
                "tasks_completed": _tasks_completed,
                "tasks_failed": _tasks_failed,
                "heartbeat_at": datetime.now(timezone.utc).isoformat(),
            }
            await redis.hset("eval:workers", worker_id, json.dumps(snapshot))
            await http_client.post(
                f"{settings.BACKEND_URL}/api/v1/workers/{worker_id}/heartbeat",
                json={
                    "status": snapshot["status"],
                    "current_task_id": snapshot["current_task_id"],
                    "cpu_percent": snapshot["cpu_percent"],
                    "memory_mb": snapshot["memory_mb"],
                    "tasks_completed": snapshot["tasks_completed"],
                    "tasks_failed": snapshot["tasks_failed"],
                },
                timeout=5.0,
            )
        except Exception as e:
            log.warning("heartbeat_failed", error=str(e))
        await asyncio.sleep(settings.HEARTBEAT_INTERVAL)
