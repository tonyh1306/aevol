from __future__ import annotations

import asyncio
import signal

import httpx
import structlog
from redis.asyncio import Redis

from worker.app.config import settings
from worker.app.consumer import consumer_loop

log = structlog.get_logger()


async def main() -> None:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    http = httpx.AsyncClient(timeout=120)
    shutdown = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown.set)

    log.info("worker_started", backend=settings.BACKEND_URL)
    try:
        await consumer_loop(redis, http, shutdown)
    finally:
        await redis.aclose()
        await http.aclose()
        log.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
