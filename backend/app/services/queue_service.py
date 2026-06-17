import json
import time
import uuid
from datetime import datetime, timezone

import structlog
from redis.asyncio import Redis

from app.config import settings

log = structlog.get_logger()

# Lua script: atomically pop from ZSET and acquire lock
# KEYS[1] = queue ZSET, KEYS[2] = unused (kept for clarity)
# ARGV[1] = worker_id, ARGV[2] = lock_ttl, ARGV[3] = now (epoch ms)
CLAIM_SCRIPT = """
local items = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[3], 'LIMIT', 0, 1)
if #items == 0 then return nil end
local payload_str = items[1]
local ok, decoded = pcall(cjson.decode, payload_str)
if not ok then
    redis.call('ZREM', KEYS[1], payload_str)
    return nil
end
local task_id = decoded['task_id']
local lock_key = 'eval:lock:' .. task_id
local acquired = redis.call('SET', lock_key, ARGV[1], 'NX', 'EX', tonumber(ARGV[2]))
if not acquired then return nil end
redis.call('ZREM', KEYS[1], payload_str)
return payload_str
"""

_claim_sha: str | None = None


async def _get_claim_sha(redis: Redis) -> str:
    global _claim_sha
    if _claim_sha is None:
        _claim_sha = await redis.script_load(CLAIM_SCRIPT)
    return _claim_sha


async def enqueue_tasks(redis: Redis, payloads: list[dict], high_priority: bool = False) -> int:
    queue = settings.HIGH_QUEUE if high_priority else settings.NORMAL_QUEUE
    now_ms = time.time() * 1000
    mapping: dict[str, float] = {}
    for p in payloads:
        score = now_ms - (p.get("priority", 0) * 1000)
        mapping[json.dumps(p)] = score
    if mapping:
        await redis.zadd(queue, mapping)
    return len(mapping)


async def claim_task(redis: Redis, worker_id: str) -> dict | None:
    sha = await _get_claim_sha(redis)
    now_ms = str(time.time() * 1000)
    for queue in (settings.HIGH_QUEUE, settings.NORMAL_QUEUE):
        result = await redis.evalsha(
            sha, 1, queue, worker_id, str(settings.TASK_LOCK_TTL), now_ms
        )
        if result:
            return json.loads(result)
    return None


async def release_lock(redis: Redis, task_id: str) -> None:
    await redis.delete(f"eval:lock:{task_id}")


async def complete_task_in_redis(redis: Redis, experiment_id: str, task_id: str) -> None:
    await release_lock(redis, task_id)
    await redis.hincrby(f"eval:experiment:{experiment_id}:progress", "completed", 1)


async def fail_task_in_redis(
    redis: Redis,
    experiment_id: str,
    task_id: str,
    payload: dict,
    attempt: int,
    max_attempts: int,
) -> bool:
    """Returns True if task was moved to DLQ (exhausted), False if scheduled for retry."""
    await release_lock(redis, task_id)
    if attempt >= max_attempts:
        await redis.rpush(settings.DEAD_QUEUE, json.dumps(payload))
        await redis.hincrby(f"eval:experiment:{experiment_id}:progress", "failed", 1)
        return True
    backoff = _compute_backoff(attempt)
    retry_at = time.time() + backoff
    payload["attempt"] = attempt + 1
    await redis.zadd(settings.RETRY_QUEUE, {json.dumps(payload): retry_at})
    return False


async def requeue_due_retries(redis: Redis) -> int:
    """Move tasks from retry ZSET to normal queue when score <= now. Returns count moved."""
    now = time.time()
    due = await redis.zrangebyscore(settings.RETRY_QUEUE, "-inf", now)
    if not due:
        return 0
    pipe = redis.pipeline()
    for item in due:
        pipe.zrem(settings.RETRY_QUEUE, item)
        pipe.zadd(settings.NORMAL_QUEUE, {item: now * 1000})
    await pipe.execute()
    return len(due)


async def publish_event(redis: Redis, event_type: str, data: dict) -> None:
    payload = json.dumps({"event": event_type, "data": data, "ts": datetime.now(timezone.utc).isoformat()})
    await redis.publish(settings.SSE_CHANNEL, payload)


async def get_queue_depths(redis: Redis) -> dict:
    high = await redis.zcard(settings.HIGH_QUEUE)
    normal = await redis.zcard(settings.NORMAL_QUEUE)
    retry = await redis.zcard(settings.RETRY_QUEUE)
    dead = await redis.llen(settings.DEAD_QUEUE)
    return {"high": high, "normal": normal, "retry": retry, "dead": dead}


async def get_experiment_progress(redis: Redis, experiment_id: str) -> dict:
    raw = await redis.hgetall(f"eval:experiment:{experiment_id}:progress")
    return {k: int(v) for k, v in raw.items()}


async def init_experiment_progress(redis: Redis, experiment_id: str, total: int) -> None:
    await redis.hset(
        f"eval:experiment:{experiment_id}:progress",
        mapping={"total": total, "completed": 0, "failed": 0},
    )


def _compute_backoff(attempt: int, base: float = 5.0, max_delay: float = 300.0) -> float:
    import random
    delay = min(max_delay, base * (2 ** attempt))
    return delay + random.uniform(0, 2)
