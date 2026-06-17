import json
import random
import time

import structlog
from redis.asyncio import Redis

from app.config import settings

log = structlog.get_logger()


def compute_backoff(attempt: int, base: float = 5.0, max_delay: float = 300.0) -> float:
    delay = min(max_delay, base * (2 ** attempt))
    return delay + random.uniform(0, 2)


async def schedule_retry(redis: Redis, task_id: str, payload: dict, attempt: int) -> None:
    max_attempts = payload.get("max_attempts", 3)
    if attempt >= max_attempts:
        await move_to_dlq(redis, task_id, payload)
        log.warning("task_exhausted", task_id=task_id, attempts=attempt)
        return

    backoff = compute_backoff(attempt)
    retry_at = time.time() + backoff
    payload["attempt"] = attempt + 1
    await redis.zadd(settings.RETRY_QUEUE, {json.dumps(payload): retry_at})
    log.info("task_scheduled_retry", task_id=task_id, attempt=attempt + 1, delay_s=round(backoff, 1))


async def move_to_dlq(redis: Redis, task_id: str, payload: dict) -> None:
    await redis.rpush(settings.DEAD_QUEUE, json.dumps(payload))
    log.error("task_dead_lettered", task_id=task_id)


async def requeue_due_retries(redis: Redis) -> int:
    now = time.time()
    due = await redis.zrangebyscore(settings.RETRY_QUEUE, "-inf", now)
    if not due:
        return 0
    pipe = redis.pipeline()
    for item in due:
        pipe.zrem(settings.RETRY_QUEUE, item)
        pipe.zadd(settings.NORMAL_QUEUE, {item: now * 1000})
    await pipe.execute()
    log.info("retries_requeued", count=len(due))
    return len(due)
