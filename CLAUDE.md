# Distributed AI Evaluation Platform — CLAUDE.md

## What This Project Is

An open-source AI evaluation platform (lightweight LangSmith/OpenAI Evals alternative).
Lets teams measure whether model/prompt/pipeline/agent changes actually improve performance.
Emphasizes distributed execution, fault tolerance, and evaluation over chatbot functionality.

## Stack

- **Backend**: FastAPI (Python 3.11), SQLAlchemy async, asyncpg
- **Database**: PostgreSQL 16 with 9 tables
- **Queue**: Redis 7 (sorted sets for priority queuing, Lua atomic claim)
- **Workers**: Python async workers with pluggable evaluators
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts
- **Infra**: Docker Compose (6 services: postgres, redis, backend, worker, frontend, nginx)

## Quick Start

```bash
cp .env.example .env
# edit .env to add ANTHROPIC_API_KEY if using llm_judge evaluator
docker compose up --build
# visit http://localhost
```

Scale workers:
```bash
docker compose up --scale worker=5
```

## Implementation Progress

### ✅ COMPLETED

**Phase 1 — Infrastructure**
- `docker-compose.yml` — 6 services with health checks, volumes, scaling support
- `docker-compose.override.yml` — dev hot-reload
- `infra/nginx/nginx.conf` — SSE-compatible reverse proxy
- `infra/postgres/init.sql` — pg_trgm extension
- `infra/redis/redis.conf` — AOF persistence, maxmemory
- `.env.example`, `.gitignore`, `Makefile`
- `backend/pyproject.toml`, `worker/pyproject.toml`
- `backend/Dockerfile`, `worker/Dockerfile`

**Phase 2 — Backend**
- `backend/app/config.py` — pydantic-settings
- `backend/app/database.py` — async SQLAlchemy engine + `get_db` dependency
- `backend/app/redis_client.py` — connection pool singleton
- `backend/alembic/` — full migration with all 9 tables + indexes
- `backend/app/models/` — all 9 ORM models
- `backend/app/schemas/` — all Pydantic request/response schemas
- `backend/app/core/` — exceptions, structured logging, correlation ID middleware
- `backend/app/services/` — all services:
  - `queue_service.py` — Lua atomic claim, retry, DLQ, SSE publish, progress counters
  - `dataset_service.py` — CSV/JSONL upload and parsing
  - `experiment_service.py` — CRUD, run/cancel/clone, completion detection
  - `task_service.py` — list, trace, failure grouping
  - `metric_service.py` — aggregate computation (mean/p50/p95/p99 via numpy)
  - `worker_service.py` — registration, heartbeats, dead worker detection
  - `report_service.py` — regression detection with configurable thresholds
  - `cluster_service.py` — TF-IDF + KMeans failure clustering
- `backend/app/api/` — all routers (experiments, datasets, tasks, workers, metrics, reports)
- `backend/app/main.py` — FastAPI app + lifespan + SSE streaming + background tasks

**Phase 3 — Workers (partially done)**
- `worker/app/config.py`
- `worker/app/evaluators/base.py` — `EvaluatorBase` ABC + `EvaluationResult` dataclass
- `worker/app/evaluators/exact_match.py`
- `worker/app/evaluators/embedding_similarity.py`
- `worker/app/evaluators/llm_judge.py` — Anthropic + OpenAI, LLM-as-judge scoring
- `worker/app/evaluators/agent_trace.py` — multi-step tool-call trace evaluation
- `worker/app/registry.py` — plugin registry with `@register` decorator
- `worker/app/retry.py` — exponential backoff + DLQ logic
- `worker/app/heartbeat.py` — periodic heartbeat to Redis + backend
- `worker/app/metrics/collector.py` — push task results + metrics to backend

### ✅ ALL PHASES COMPLETE

**Phase 3 (complete)**
- [x] `worker/app/consumer.py` — Lua atomic claim, retry/DLQ branching, SSE publish
- [x] `worker/app/main.py` — register, gather consumer+heartbeat+retry loops, SIGTERM shutdown

**Phase 4 — Advanced backend endpoints (complete)**
- [x] `backend/app/api/tasks.py` — added `PATCH /tasks/{id}/result`, `POST /tasks/{id}/metrics`, `POST /tasks/{id}/traces`

**Phase 5 — Frontend (complete)**
- [x] `frontend/package.json` + `next.config.ts` + `tailwind.config.js` + `Dockerfile`
- [x] `frontend/src/lib/api.ts` — typed fetch client
- [x] `frontend/src/lib/types.ts` — TypeScript types
- [x] Layout: `layout.tsx`, `Sidebar.tsx`, `TopBar.tsx`
- [x] Experiments list, detail (live SSE), new wizard, compare pages
- [x] Datasets list + detail, Workers dashboard, Reports list + detail
- [x] Hooks: `useSSE.ts`, `useExperiments.ts`, `useWorkers.ts`
- [x] Components: `StatusBadge`, `EmptyState`, `TaskProgressBar`, `MetricsSummary`

**Phase 6 — Hardening (complete)**
- [x] `scripts/seed_demo_data.py`
- [x] `scripts/benchmark_workers.py`
- [x] `README.md` with full quickstart and architecture docs

---

## Key Architecture Details

### Redis Queue Names
```
eval:queue:high        ZSET — high-priority tasks
eval:queue:normal      ZSET — standard tasks (score = enqueue_time_ms)
eval:queue:retry       ZSET — score = next_retry_at epoch seconds
eval:queue:dead        LIST — exhausted tasks
eval:workers           HASH — worker_id → JSON heartbeat snapshot
eval:lock:{task_id}    STRING TTL=60s — prevents double-execution
eval:experiment:{id}:progress  HASH — total/completed/failed
eval:sse:channel       PubSub — SSE events to frontend
```

### Task Status Flow
`PENDING → RUNNING → COMPLETED/FAILED → DEAD` (after max retries)

### Worker consumer.py spec (next to implement)
```python
async def consumer_loop(worker_id, redis, http_client, shutdown_event):
    while not shutdown_event.is_set():
        payload = await claim_task(redis, worker_id)  # Lua atomic pop+lock
        if not payload:
            await asyncio.sleep(POLL_INTERVAL); continue
        task_id = payload["task_id"]
        experiment_id = payload["experiment_id"]
        attempt = payload["attempt"]

        heartbeat.set_current_task(task_id)
        await update_task_status_via_http(http_client, task_id, "RUNNING", worker_id)

        evaluator = registry.get(payload["evaluator_type"])
        t0 = time.monotonic()
        try:
            result = await evaluator.evaluate(payload)
            latency_ms = int((time.monotonic() - t0) * 1000)
            await complete_task_in_redis(redis, experiment_id, task_id)
            await push_metrics(http_client, task_id, experiment_id, result, latency_ms)
            await publish_event(redis, "task_completed", {...})
            heartbeat.record_completed()
        except RetryableError as e:
            await schedule_retry(redis, task_id, payload, attempt)
            await update_task_status_via_http(http_client, task_id, "PENDING", error=str(e))
        except Exception as e:
            await move_to_dlq(redis, task_id, payload)
            await update_task_status_via_http(http_client, task_id, "FAILED", error=str(e))
            heartbeat.record_failed()
        finally:
            heartbeat.set_current_task(None)
```

### worker/app/main.py spec
```python
async def main():
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    http_client = httpx.AsyncClient()
    shutdown_event = asyncio.Event()

    # SIGTERM handler: set shutdown_event
    # Register with backend
    response = await http_client.post(f"{settings.BACKEND_URL}/api/v1/workers/register", json={...})
    worker_id = response.json()["id"]

    await asyncio.gather(
        consumer_loop(worker_id, redis, http_client, shutdown_event),
        heartbeat_loop(redis, http_client, worker_id, shutdown_event),
        retry_requeue_loop(redis, shutdown_event),   # leader-elected
    )
    # deregister on exit

if __name__ == "__main__":
    asyncio.run(main())
```

### Backend endpoints worker needs (add these to tasks.py)
```
PATCH /api/v1/tasks/{id}/result  — update task status, output, latency, cost
POST  /api/v1/tasks/{id}/metrics — bulk insert metrics
POST  /api/v1/tasks/{id}/traces  — bulk insert agent trace steps
```

### Frontend API base URL
- In Docker: `NEXT_PUBLIC_API_URL=""` (nginx proxies `/api/` to backend)
- Local dev without nginx: `NEXT_PUBLIC_API_URL=http://localhost:8000`

## All API Routes

```
GET  /api/v1/health
GET  /api/v1/ready

# Experiments
GET    /api/v1/experiments
POST   /api/v1/experiments
GET    /api/v1/experiments/{id}
PATCH  /api/v1/experiments/{id}
DELETE /api/v1/experiments/{id}
POST   /api/v1/experiments/{id}/run
POST   /api/v1/experiments/{id}/cancel
POST   /api/v1/experiments/{id}/clone
GET    /api/v1/experiments/{id}/tasks
GET    /api/v1/experiments/{id}/metrics/summary
GET    /api/v1/experiments/{id}/failures
GET    /api/v1/experiments/{id}/clusters
GET    /api/v1/experiments/{a}/compare/{b}

# Datasets
GET    /api/v1/datasets
POST   /api/v1/datasets/upload
GET    /api/v1/datasets/{id}
GET    /api/v1/datasets/{id}/rows
DELETE /api/v1/datasets/{id}

# Tasks (worker-facing + API)
GET    /api/v1/tasks/{id}
POST   /api/v1/tasks/{id}/retry
GET    /api/v1/tasks/{id}/trace
PATCH  /api/v1/tasks/{id}/result      ← worker pushes result here
POST   /api/v1/tasks/{id}/metrics     ← worker pushes metrics here
POST   /api/v1/tasks/{id}/traces      ← worker pushes agent traces here

# Workers
GET    /api/v1/workers
POST   /api/v1/workers/register
POST   /api/v1/workers/{id}/heartbeat
GET    /api/v1/workers/{id}
DELETE /api/v1/workers/{id}

# Metrics
GET    /api/v1/metrics/names
GET    /api/v1/metrics/experiments/{id}

# Reports
POST   /api/v1/reports
GET    /api/v1/reports
GET    /api/v1/reports/{id}

# SSE streaming
GET    /api/v1/stream/experiments/{id}
GET    /api/v1/stream/workers
```

## Verification Checklist

1. `docker compose up --build` → all 6 services healthy
2. `curl http://localhost/api/v1/health` → `{"status":"ok"}`
3. Upload CSV dataset → `POST /api/v1/datasets/upload`
4. Create + run experiment with `exact_match` evaluator
5. Observe live task progress via SSE: `curl http://localhost/api/v1/stream/experiments/{id}`
6. Scale to 5 workers: `docker compose up --scale worker=5`
7. Kill a worker mid-run → task re-enqueued within 30s
8. Generate comparison report between two experiments
9. Verify failure clustering on a failed experiment
