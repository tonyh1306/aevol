# agentjudge

LLM-as-judge evaluation for multi-agent applications. Submit your agent's execution trace, define a rubric, and get back structured scores with reasoning — without conforming to someone else's opinionated schema.

## Why

Existing eval tools either evaluate flat LLM outputs or force you to conform to their data model. agentjudge gives you a universal trace schema that maps onto any agent framework — LangGraph, CrewAI, AutoGen, raw API calls — and judges the full execution: tool calls, handoffs, chain-of-thought, intermediate outputs, and final answer.

## Schema

The schema is the product. You can see exactly what you're submitting.

```python
from agentjudge import Trace, Span, Content, AgentInfo

trace = Trace(
    input=Content(content="Book me a flight to Paris next Friday"),
    expected=Content(content="Confirmed booking with confirmation number"),
    spans=[
        Span(
            id="s1",
            type="llm",
            agent=AgentInfo(name="orchestrator", model="claude-sonnet-4-6"),
            input=Content(content="Book me a flight to Paris next Friday"),
            reasoning="I need to search for flights first, then book the best option.",
            output=Content(content="I'll search for available flights."),
        ),
        Span(
            id="s2",
            parent_id="s1",
            type="tool",
            input=Content(content='{"origin":"JFK","destination":"CDG","date":"2026-07-04"}', content_type="json"),
            output=Content(content='{"flights":[{"id":"AF123","price":420}]}', content_type="json"),
        ),
        Span(
            id="s3",
            parent_id="s1",
            type="tool",
            input=Content(content='{"flight_id":"AF123"}', content_type="json"),
            output=Content(content='{"confirmation":"XY9921"}', content_type="json"),
        ),
    ],
)
```

`Span.type` is one of `llm | tool | handoff | agent`. Spans nest via `parent_id`. That's it.

## Evaluate

```python
from agentjudge import evaluate, Rubric, Criterion, JudgeConfig

rubric = Rubric(
    name="Travel booking",
    criteria=[
        Criterion(name="goal_completion", description="Did the agent successfully book a flight?", weight=2.0),
        Criterion(name="tool_efficiency", description="Did the agent use the minimum necessary tool calls?", weight=1.0),
        Criterion(name="reasoning_quality", description="Was the agent's reasoning coherent and correct?", weight=1.0),
    ],
)

result = await evaluate(trace, rubric, JudgeConfig(provider="anthropic", model="claude-sonnet-4-6"))

print(result.overall_score)   # 0.91
print(result.passed)          # True
for s in result.scores:
    print(s.criterion, s.score, s.reasoning)
```

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │            agentjudge SDK            │
                        │  evaluate(trace, rubric, config)     │
                        │  ─ render trace tree to text         │
                        │  ─ build judge prompt                │
                        │  ─ call Anthropic / OpenAI           │
                        │  ─ parse + weight scores             │
                        └──────────────┬──────────────────────┘
                                       │ used by
              ┌────────────────────────▼────────────────────────┐
              │                   Worker (×N)                    │
              │  BRPOP agentjudge:runs                          │
              │  → fetch rubric + trace from backend            │
              │  → call SDK evaluate()                          │
              │  → PATCH result back to backend                 │
              └────────────────┬────────────────────────────────┘
                               │ HTTP
┌──────────────┐   HTTP/SSE   ▼──────────────┐   SQL    ┌──────────────────────┐
│   Next.js    │◀────────────│    FastAPI     │─────────▶│     PostgreSQL 16     │
│   Frontend   │             │    Backend     │          │  rubrics             │
└──────────────┘             └───────┬────────┘          │  traces              │
                                     │                   │  runs                │
                              LPUSH / SUBSCRIBE          │  evaluations         │
                                     │                   └──────────────────────┘
                              ┌──────▼───────┐
                              │    Redis 7   │
                              │  agentjudge: │
                              │    :runs     │  ← LIST  (worker queue)
                              │    :sse      │  ← PubSub (SSE fan-out)
                              └──────────────┘
```

Flow: client calls `POST /runs` → backend creates evaluation rows and pushes to Redis → workers pop, call the SDK, patch results back → frontend streams live progress via SSE.

## Quick Start (self-hosted)

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY or OPENAI_API_KEY
docker compose up --build
```

API at http://localhost:8000/api/v1 — interactive docs at http://localhost:8000/docs.

Scale workers:

```bash
docker compose up --scale worker=5
```

## API

```
POST /api/v1/rubrics               Create a rubric
GET  /api/v1/rubrics               List rubrics
GET  /api/v1/rubrics/{id}          Get rubric

POST /api/v1/traces                Submit a trace
GET  /api/v1/traces/{id}           Get trace

POST /api/v1/runs                  Start an evaluation run
GET  /api/v1/runs                  List runs
GET  /api/v1/runs/{id}             Get run + progress
GET  /api/v1/runs/{id}/evaluations Per-trace results

GET  /api/v1/stream/runs/{id}      SSE live evaluation progress
```

## Stack

| Component | Technology |
|-----------|------------|
| SDK | Python 3.11, Pydantic v2 |
| Backend | FastAPI, SQLAlchemy async, asyncpg |
| Database | PostgreSQL 16 (4 tables) |
| Queue | Redis 7 |
| Workers | Python asyncio |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Deployment | Docker Compose |

## Supported Judge Providers

| Provider | Models |
|----------|--------|
| Anthropic | claude-sonnet-4-6, claude-opus-4-8, any `claude-*` |
| OpenAI | gpt-4o, gpt-4-turbo, any OpenAI model |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Required if using Anthropic as judge |
| `OPENAI_API_KEY` | Required if using OpenAI as judge |
| `POSTGRES_PASSWORD` | Database password |

## License

MIT
