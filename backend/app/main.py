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
from app.api import rubrics, traces, runs, evaluations

configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("db_connected")
    yield
    await close_redis()
    log.info("shutdown_complete")


app = FastAPI(
    title="agentjudge",
    version="0.1.0",
    description="LLM-as-judge evaluation for multi-agent applications.",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CorrelationIDMiddleware)

PREFIX = "/api/v1"
app.include_router(rubrics.router, prefix=PREFIX)
app.include_router(traces.router, prefix=PREFIX)
app.include_router(runs.router, prefix=PREFIX)
app.include_router(evaluations.router, prefix=PREFIX)


@app.get(f"{PREFIX}/health")
async def health():
    return {"status": "ok", "service": "agentjudge"}


@app.get(f"{PREFIX}/ready")
async def ready():
    try:
        redis = get_redis()
        await redis.ping()
        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


@app.get(f"{PREFIX}/stream/runs/{{run_id}}")
async def stream_run(run_id: str):
    return StreamingResponse(
        _run_sse_generator(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _run_sse_generator(run_id: str):
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe("agentjudge:sse")
    try:
        yield f"data: {json.dumps({'event': 'connected', 'run_id': run_id})}\n\n"
        async for message in pubsub.listen():
            if message["type"] == "message":
                payload = json.loads(message["data"])
                if payload.get("run_id") == run_id:
                    yield f"data: {message['data']}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("agentjudge:sse")
        await pubsub.aclose()
