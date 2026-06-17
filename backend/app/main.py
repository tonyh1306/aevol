import asyncio
import json
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.logging import configure_logging
from app.core.middleware import CorrelationIDMiddleware
from app.database import init_db
from app.redis_client import close_redis, get_redis
from app.api import experiments, datasets, tasks, workers, metrics, reports
from app.services.worker_service import detect_dead_workers
from app.services.queue_service import get_queue_depths, requeue_due_retries
from app.config import settings

configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("db_connected")

    # Background tasks
    dead_worker_task = asyncio.create_task(_dead_worker_monitor())
    retry_sweep_task = asyncio.create_task(_retry_sweep())
    dlq_monitor_task = asyncio.create_task(_dlq_monitor())

    yield

    dead_worker_task.cancel()
    retry_sweep_task.cancel()
    dlq_monitor_task.cancel()
    await close_redis()
    log.info("shutdown_complete")


app = FastAPI(
    title="Distributed AI Evaluation Platform",
    version="0.1.0",
    description="Measure whether changes to models, prompts, and agents actually improve performance.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIDMiddleware)

PREFIX = "/api/v1"
app.include_router(experiments.router, prefix=PREFIX)
app.include_router(datasets.router, prefix=PREFIX)
app.include_router(tasks.router, prefix=PREFIX)
app.include_router(workers.router, prefix=PREFIX)
app.include_router(metrics.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)


@app.get(f"{PREFIX}/health")
async def health():
    return {"status": "ok", "service": "eval-backend"}


@app.get(f"{PREFIX}/ready")
async def ready():
    try:
        redis = get_redis()
        await redis.ping()
        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


@app.get(f"{PREFIX}/stream/experiments/{{experiment_id}}")
async def stream_experiment(experiment_id: str):
    """SSE stream for real-time task progress updates."""
    return StreamingResponse(
        _sse_generator(experiment_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get(f"{PREFIX}/stream/workers")
async def stream_workers():
    """SSE stream for worker health updates."""
    return StreamingResponse(
        _worker_sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _sse_generator(experiment_id: str):
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(settings.SSE_CHANNEL)
    try:
        yield f"data: {json.dumps({'event': 'connected', 'experiment_id': experiment_id})}\n\n"
        async for message in pubsub.listen():
            if message["type"] == "message":
                payload = json.loads(message["data"])
                if payload.get("data", {}).get("experiment_id") == experiment_id:
                    yield f"data: {message['data']}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(settings.SSE_CHANNEL)
        await pubsub.aclose()


async def _worker_sse_generator():
    redis = get_redis()
    try:
        while True:
            workers_data = await redis.hgetall("eval:workers")
            payload = json.dumps({
                "event": "worker_update",
                "data": {k: json.loads(v) for k, v in workers_data.items()},
            })
            yield f"data: {payload}\n\n"
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass


async def _dead_worker_monitor():
    from app.database import async_session_factory
    while True:
        try:
            await asyncio.sleep(15)
            async with async_session_factory() as db:
                dead = await detect_dead_workers(db)
                if dead:
                    log.warning("dead_workers_detected", count=len(dead))
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("dead_worker_monitor_error", error=str(e))


async def _retry_sweep():
    redis = get_redis()
    while True:
        try:
            await asyncio.sleep(5)
            moved = await requeue_due_retries(redis)
            if moved:
                log.info("retries_requeued", count=moved)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("retry_sweep_error", error=str(e))


async def _dlq_monitor():
    redis = get_redis()
    while True:
        try:
            await asyncio.sleep(300)
            depths = await get_queue_depths(redis)
            if depths["dead"] > 0:
                log.warning("dead_letter_queue_has_items", count=depths["dead"])
            log.info("queue_depths", **depths)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("dlq_monitor_error", error=str(e))
