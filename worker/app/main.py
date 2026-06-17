import asyncio
import os
import signal
import socket

import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.registry import load_all
from app.consumer import consumer_loop
from app.heartbeat import heartbeat_loop
from app.retry import requeue_due_retries

log = structlog.get_logger()


async def _retry_sweep_loop(redis: Redis, shutdown_event: asyncio.Event) -> None:
    """Leader-elected retry sweep: only one worker runs this at a time."""
    while not shutdown_event.is_set():
        try:
            worker_id = os.environ.get("WORKER_ID", "")
            acquired = await redis.set(
                "eval:retry-leader", worker_id, nx=True, ex=20
            )
            if acquired:
                moved = await requeue_due_retries(redis)
                if moved:
                    log.info("retry_sweep_moved", count=moved)
        except Exception as e:
            log.warning("retry_sweep_error", error=str(e))
        await asyncio.sleep(10)


async def _register_worker(http_client: httpx.AsyncClient) -> str:
    hostname = socket.gethostname()
    pid = os.getpid()

    for attempt in range(10):
        try:
            response = await http_client.post(
                f"{settings.BACKEND_URL}/api/v1/workers/register",
                json={
                    "hostname": hostname,
                    "pid": pid,
                    "version": settings.WORKER_VERSION,
                    "capabilities": ["exact_match", "embedding_similarity", "llm_judge", "agent_trace"],
                },
                timeout=10.0,
            )
            response.raise_for_status()
            worker_id = response.json()["id"]
            log.info("worker_registered", worker_id=worker_id, hostname=hostname, pid=pid)
            return worker_id
        except Exception as e:
            log.warning("registration_failed", attempt=attempt + 1, error=str(e))
            await asyncio.sleep(5 * (attempt + 1))

    raise RuntimeError("Could not register with backend after 10 attempts")


async def _deregister_worker(http_client: httpx.AsyncClient, worker_id: str) -> None:
    try:
        await http_client.delete(
            f"{settings.BACKEND_URL}/api/v1/workers/{worker_id}",
            timeout=5.0,
        )
        log.info("worker_deregistered", worker_id=worker_id)
    except Exception as e:
        log.warning("deregister_failed", error=str(e))


async def main() -> None:
    import logging
    import structlog as sl

    sl.configure(
        processors=[
            sl.contextvars.merge_contextvars,
            sl.processors.add_log_level,
            sl.processors.TimeStamper(fmt="iso"),
            sl.processors.JSONRenderer(),
        ],
        wrapper_class=sl.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        logger_factory=sl.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=settings.LOG_LEVEL.upper())

    load_all()
    log.info("evaluators_loaded")

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def handle_signal():
        log.info("shutdown_signal_received")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    http_client = httpx.AsyncClient()

    try:
        worker_id = await _register_worker(http_client)

        await asyncio.gather(
            consumer_loop(worker_id, redis, http_client, shutdown_event),
            heartbeat_loop(redis, http_client, worker_id, shutdown_event),
            _retry_sweep_loop(redis, shutdown_event),
        )
    finally:
        if "worker_id" in dir():
            await _deregister_worker(http_client, worker_id)
        await http_client.aclose()
        await redis.aclose()
        log.info("worker_shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
