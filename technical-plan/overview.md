# agentjudge — Technical Plan

## Project Directory

```
agentjudge/
├── sdk/                        Python package — install and use standalone
│   ├── pyproject.toml          Package manifest (name: agentjudge)
│   └── agentjudge/
│       ├── __init__.py         Public API: evaluate(), Trace, Span, Content, Rubric, etc.
│       ├── schema.py           All Pydantic models (Trace, Span, Content, Rubric, EvaluationResult, ...)
│       ├── judge.py            evaluate() entrypoint — routes to the correct provider
│       └── providers/
│           ├── base.py         JudgeProvider ABC, render_trace(), build_judge_prompt()
│           ├── anthropic.py    AnthropicJudge — calls claude-* models, parses JSON response
│           └── openai.py       OpenAIJudge — calls gpt-* models via json_object response format
│
├── backend/                    FastAPI service — persistence, queuing, SSE
│   ├── Dockerfile
│   ├── pyproject.toml          name: agentjudge-backend
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              Async alembic runner, reads DATABASE_URL from env
│   │   └── versions/
│   │       └── 001_initial_schema.py   Creates all 4 tables
│   └── app/
│       ├── main.py             FastAPI app, lifespan, CORS, router mounts, SSE endpoint
│       ├── config.py           pydantic-settings: DATABASE_URL, REDIS_URL, API keys
│       ├── database.py         Async SQLAlchemy engine, session factory, get_db dependency
│       ├── redis_client.py     Redis connection pool singleton
│       ├── core/
│       │   ├── exceptions.py   HTTP exception handlers
│       │   ├── logging.py      structlog configuration
│       │   └── middleware.py   Correlation ID middleware
│       ├── models/             SQLAlchemy ORM models (one file per table)
│       │   ├── rubric.py
│       │   ├── trace.py
│       │   ├── run.py
│       │   └── evaluation.py
│       ├── schemas/            Pydantic request/response schemas
│       │   ├── rubric.py       RubricCreate, RubricResponse
│       │   ├── trace.py        TraceCreate, TraceResponse, SpanSchema, ContentSchema
│       │   ├── run.py          RunCreate, RunResponse, JudgeConfigSchema
│       │   └── evaluation.py   EvaluationResponse, CriterionScoreSchema
│       ├── services/           Business logic, no HTTP concerns
│       │   ├── rubric_service.py   create, get, list rubrics
│       │   ├── trace_service.py    create, get, get_many traces
│       │   └── run_service.py      create run + evaluations, enqueue to Redis,
│       │                           mark_evaluation_done/failed, publish SSE events
│       └── api/                FastAPI routers
│           ├── deps.py         get_db dependency
│           ├── rubrics.py      POST/GET /rubrics
│           ├── traces.py       POST/GET /traces
│           ├── runs.py         POST/GET /runs, GET /runs/{id}/evaluations
│           └── evaluations.py  PATCH /runs/{id}/evaluations/{id} (worker callback)
│
├── worker/                     Async worker — consumes Redis queue, calls SDK, reports results
│   ├── Dockerfile              Build context is repo root so it can COPY sdk/
│   ├── pyproject.toml          name: agentjudge-worker
│   └── app/
│       ├── __init__.py
│       ├── config.py           REDIS_URL, BACKEND_URL, API keys
│       ├── consumer.py         consumer_loop() — brpop from agentjudge:runs,
│       │                       fetch rubric + trace, call evaluate(), PATCH result back
│       └── main.py             asyncio entry point, SIGTERM handler
│
├── frontend/                   Next.js 14 dashboard (needs rebuild for new API)
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       └── ...                 Currently stale — pages reference old API routes
│
├── infra/
│   ├── nginx/nginx.conf        Reverse proxy: /api/ → backend:8000, / → frontend:3000
│   ├── postgres/init.sql       Enable pgcrypto, set timezone UTC
│   └── redis/redis.conf        AOF persistence, LRU eviction, 512mb maxmemory
│
├── technical-plan/
│   └── overview.md             This file
│
├── docker-compose.yml          6 services: postgres, redis, backend, worker (×2), frontend, nginx
├── docker-compose.override.yml Dev hot-reload for backend, worker, frontend
├── .env.example                Template for required env vars
├── Makefile                    Convenience targets
└── README.md
```

---

## Database Tables

### `rubrics`

Stores reusable evaluation rubrics. A rubric defines what to judge and how to weight each criterion.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | TEXT | Human label |
| description | TEXT | Optional |
| criteria | JSONB | `[{name, description, weight}]` — weight is a float used for weighted average |
| created_at | TIMESTAMPTZ | |

### `traces`

Stores a single agent execution. Spans are stored as JSONB — no separate table — because span structure is variable and queried as a unit, never individually.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| input | JSONB | `{content, content_type}` — what the user/system sent to the agent |
| expected | JSONB | `{content, content_type}` — ground truth, optional |
| spans | JSONB | `[Span, ...]` — full execution tree; parent_id links form the tree structure |
| metadata | JSONB | Arbitrary k/v (env, version, tags) |
| created_at | TIMESTAMPTZ | |

### `runs`

A batch evaluation job: one rubric applied to N traces using a specific judge model.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | TEXT | Human label |
| rubric_id | UUID FK → rubrics | |
| judge_config | JSONB | `{provider, model, temperature}` |
| status | TEXT | `pending \| running \| completed \| failed` |
| total | INT | Number of traces in this run |
| completed | INT | Evaluations that finished successfully |
| failed | INT | Evaluations that errored |
| created_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | Set when `completed + failed == total` |

### `evaluations`

One row per (run, trace) pair. Created as `pending` when the run is created; updated by the worker when the judge returns.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| run_id | UUID FK → runs | |
| trace_id | UUID FK → traces | |
| scores | JSONB | `[{criterion, score, reasoning}]` — null until completed |
| overall_score | FLOAT | Weighted average of scores — null until completed |
| passed | BOOL | `overall_score >= 0.7` — null until completed |
| reasoning | TEXT | Judge's overall assessment |
| error | TEXT | Error message if status = failed |
| status | TEXT | `pending \| running \| completed \| failed` |
| created_at | TIMESTAMPTZ | |

Indexes: `ix_evaluations_run_id`, `ix_evaluations_trace_id`, `ix_runs_status`

---

## Redis Keys

| Key | Type | Purpose |
|-----|------|---------|
| `agentjudge:runs` | LIST | Run payloads queued for workers (LPUSH by backend, BRPOP by worker) |
| `agentjudge:sse` | PubSub channel | Events published by run_service, subscribed by SSE endpoint in backend |

---

## Data Flow

```
User submits POST /runs
  → backend creates Run + N Evaluation rows (status=pending)
  → backend LPUSH run payload to agentjudge:runs
  → returns run_id immediately

Worker BRPOP agentjudge:runs
  → fetches rubric from backend
  → fetches each trace from backend
  → calls evaluate(trace, rubric, judge_config) from SDK
    → SDK renders trace tree to text
    → SDK sends prompt to judge LLM
    → SDK parses JSON scores, computes weighted average
  → PATCH /runs/{id}/evaluations/{id} with result
    → backend updates evaluation row
    → backend increments run.completed / run.failed
    → backend publishes SSE event to agentjudge:sse

Browser GET /stream/runs/{id}
  → backend subscribes to agentjudge:sse
  → filters events by run_id
  → streams matching events as SSE
```

---

## SDK Usage (standalone, no backend)

```python
import asyncio
from agentjudge import evaluate, Trace, Span, Content, Rubric, Criterion, JudgeConfig

async def main():
    trace = Trace(
        input=Content(content="Summarize the quarterly report"),
        spans=[
            Span(type="llm", input=Content(content="..."), output=Content(content="...")),
        ],
    )
    rubric = Rubric(
        name="Summarization quality",
        criteria=[
            Criterion(name="completeness", description="Does the summary cover all key points?"),
            Criterion(name="conciseness", description="Is the summary appropriately brief?"),
        ],
    )
    result = await evaluate(trace, rubric, JudgeConfig(provider="anthropic"))
    print(result.overall_score, result.passed)

asyncio.run(main())
```

The SDK has no dependency on the backend. Install with `pip install ./sdk`.
