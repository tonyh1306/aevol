# Distributed AI Evaluation Platform

A production-quality open-source platform for measuring whether changes to models, prompts, retrieval pipelines, or agents actually improve performance.

Inspired by LangSmith, OpenAI Evals, and CI/CD infrastructure for AI systems — with emphasis on **distributed execution**, **fault tolerance**, and **evaluation** rather than chatbot functionality.

## Features

- **Experiment management** — create, version, clone, run, and compare experiments
- **Dataset upload** — CSV and JSONL support with schema inference
- **Distributed task execution** — Redis-backed priority queue with Lua atomic claiming
- **Worker pool** — horizontal scaling (`--scale worker=N`), auto-restart on failure
- **Fault tolerance** — heartbeat monitoring, dead worker detection, automatic re-queueing
- **Retry with backoff** — exponential backoff + dead-letter queue for exhausted tasks
- **Evaluator plugins** — exact_match, embedding_similarity, llm_judge, agent_trace
- **Live dashboard** — real-time task progress via Server-Sent Events
- **Regression detection** — compare experiment versions, flag performance regressions
- **Failure clustering** — TF-IDF + KMeans groups error messages, generates repair suggestions
- **Agent evaluation** — captures tool-call traces, evaluates multi-step execution

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Next.js    │────▶│   FastAPI   │────▶│  PostgreSQL  │
│  Frontend   │◀────│   Backend   │     │  (9 tables)  │
└─────────────┘ SSE └──────┬──────┘     └──────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │  (queues)   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
         ┌────▼────┐  ┌────▼────┐  ┌───▼─────┐
         │ Worker  │  │ Worker  │  │ Worker  │
         │  (×N)   │  │  (×N)   │  │  (×N)   │
         └─────────┘  └─────────┘  └─────────┘
```

## Quick Start

```bash
git clone <repo>
cd distributed-agent
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY if using llm_judge evaluator
docker compose up --build
```

Open http://localhost — the dashboard is live.

### Seed demo data

```bash
make seed
# or: docker compose exec backend python /scripts/seed_demo_data.py
```

### Scale workers

```bash
docker compose up --scale worker=10
# or: make scale-workers N=10
```

## Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, SQLAlchemy async, asyncpg |
| Database | PostgreSQL 16 |
| Queue | Redis 7 (sorted sets + Lua scripts) |
| Workers | Python 3.11 asyncio |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Charts | Recharts |
| Deployment | Docker Compose |

## Evaluator Types

| Type | Description |
|------|-------------|
| `exact_match` | String/token exact match + token overlap |
| `embedding_similarity` | TF-IDF cosine similarity |
| `llm_judge` | Run model → judge output with a separate LLM |
| `agent_trace` | Multi-step agent with tool-call trace evaluation |

## API Reference

The backend exposes a REST API at `http://localhost:8000/api/v1`.

Interactive docs: http://localhost:8000/docs

Key endpoints:

```
POST /api/v1/datasets/upload          Upload CSV or JSONL dataset
POST /api/v1/experiments              Create experiment
POST /api/v1/experiments/{id}/run     Start evaluation
GET  /api/v1/experiments/{id}/tasks   List tasks with status
GET  /api/v1/experiments/{id}/metrics/summary  Aggregate metrics
GET  /api/v1/experiments/{a}/compare/{b}       Regression comparison
POST /api/v1/reports                  Generate regression report
GET  /api/v1/workers                  Worker health
GET  /api/v1/stream/experiments/{id}  SSE live updates
```

## Development

```bash
# Backend hot reload
docker compose -f docker-compose.yml -f docker-compose.override.yml up

# Run migration
make migrate

# Benchmark throughput
docker compose exec backend python /scripts/benchmark_workers.py --tasks 200

# Queue depths
make queue-stats
```

## Environment Variables

See `.env.example` for all options. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_PASSWORD` | `changeme` | PostgreSQL password |
| `ANTHROPIC_API_KEY` | — | Required for `llm_judge` evaluator |
| `OPENAI_API_KEY` | — | Alternative LLM provider |
| `WORKER_DEAD_THRESHOLD` | `30` | Seconds before worker marked dead |
| `TASK_LOCK_TTL` | `60` | Task lock TTL in seconds |

## Distributed Systems Design

- **Atomic task claiming**: Lua script atomically pops from Redis ZSET and sets a lock — prevents double-execution even under concurrent workers
- **Priority queues**: Two sorted sets (`high`, `normal`) scored by enqueue time; high-priority tasks are always polled first
- **Retry with jitter**: Exponential backoff `min(300, 5 × 2^attempt) + random(0,2)` prevents thundering herd on transient failures
- **Dead worker recovery**: Backend background task scans heartbeats every 15s; tasks claimed by dead workers are re-queued within `WORKER_DEAD_THRESHOLD` seconds
- **Leader election**: Only one worker runs the retry-sweep loop at a time via Redis `SET NX EX`
- **SSE fan-out**: Workers publish events to a Redis Pub/Sub channel; the backend streams them to all connected browsers via Server-Sent Events

## License

MIT
