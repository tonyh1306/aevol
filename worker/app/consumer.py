import asyncio
import json
import time

import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.evaluators.base import RetryableError
from app.metrics.collector import push_metrics
from app.retry import move_to_dlq, schedule_retry
from app import heartbeat as hb
from app import registry

log = structlog.get_logger()

# Lua script: atomically pop from ZSET + acquire lock
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


async def claim_task(redis: Redis, worker_id: str) -> dict | None:
    sha = await _get_claim_sha(redis)
    now_ms = str(time.time() * 1000)
    for queue in (settings.HIGH_QUEUE, settings.NORMAL_QUEUE):
        result = await redis.evalsha(sha, 1, queue, worker_id, str(settings.TASK_LOCK_TTL), now_ms)
        if result:
            return json.loads(result)
    return None


async def release_lock(redis: Redis, task_id: str) -> None:
    await redis.delete(f"eval:lock:{task_id}")


async def _update_task_status(
    http_client: httpx.AsyncClient,
    task_id: str,
    status: str,
    worker_id: str | None = None,
    error: str | None = None,
    error_type: str | None = None,
) -> None:
    body: dict = {"status": status}
    if worker_id:
        body["worker_id"] = worker_id
    if error:
        body["error_message"] = error[:2000]
    if error_type:
        body["error_type"] = error_type
    try:
        await http_client.patch(
            f"{settings.BACKEND_URL}/api/v1/tasks/{task_id}/result",
            json=body,
            timeout=5.0,
        )
    except Exception as e:
        log.warning("status_update_failed", task_id=task_id, error=str(e))


async def _publish_event(redis: Redis, event_type: str, data: dict) -> None:
    from datetime import datetime, timezone
    payload = json.dumps({"event": event_type, "data": data, "ts": datetime.now(timezone.utc).isoformat()})
    await redis.publish(settings.SSE_CHANNEL, payload)


async def consumer_loop(
    worker_id: str,
    redis: Redis,
    http_client: httpx.AsyncClient,
    shutdown_event: asyncio.Event,
) -> None:
    log.info("consumer_started", worker_id=worker_id)
    while not shutdown_event.is_set():
        payload = await claim_task(redis, worker_id)
        if not payload:
            await asyncio.sleep(settings.POLL_INTERVAL)
            continue

        task_id = payload["task_id"]
        experiment_id = payload["experiment_id"]
        attempt = payload.get("attempt", 1)
        evaluator_type = payload.get("evaluator_type", "exact_match")

        hb.set_current_task(task_id)
        log.info("task_claimed", task_id=task_id, evaluator=evaluator_type, attempt=attempt)

        await _update_task_status(http_client, task_id, "RUNNING", worker_id=worker_id)

        t0 = time.monotonic()
        try:
            evaluator = registry.get(evaluator_type)
            result = await evaluator.evaluate(payload)
            latency_ms = int((time.monotonic() - t0) * 1000)

            await release_lock(redis, task_id)
            await redis.hincrby(f"eval:experiment:{experiment_id}:progress", "completed", 1)

            await push_metrics(http_client, task_id, experiment_id, result, latency_ms)
            await _publish_event(redis, "task_completed", {
                "task_id": task_id,
                "experiment_id": experiment_id,
                "status": "COMPLETED",
                "latency_ms": latency_ms,
                "metrics": result.metrics,
            })

            hb.record_completed()
            log.info("task_completed", task_id=task_id, latency_ms=latency_ms)

        except RetryableError as e:
            await release_lock(redis, task_id)
            await schedule_retry(redis, task_id, payload, attempt)
            await _update_task_status(
                http_client, task_id, "PENDING", error=str(e), error_type=type(e).__name__
            )
            await redis.hincrby(f"eval:experiment:{experiment_id}:progress", "failed", 1)
            log.warning("task_retrying", task_id=task_id, attempt=attempt, error=str(e))

        except Exception as e:
            await release_lock(redis, task_id)
            await move_to_dlq(redis, task_id, payload)
            await _update_task_status(
                http_client, task_id, "FAILED", error=str(e), error_type=type(e).__name__
            )
            await redis.hincrby(f"eval:experiment:{experiment_id}:progress", "failed", 1)
            await _publish_event(redis, "task_failed", {
                "task_id": task_id,
                "experiment_id": experiment_id,
                "status": "FAILED",
                "error": str(e)[:500],
            })
            hb.record_failed()
            log.error("task_failed", task_id=task_id, error=str(e), exc_info=True)

        finally:
            hb.set_current_task(None)
