from __future__ import annotations

import asyncio
import json

import httpx
import structlog
from redis.asyncio import Redis

from agentjudge import Rubric, Trace, evaluate
from agentjudge.schema import Criterion, JudgeConfig

from worker.app.config import settings

log = structlog.get_logger()


async def consumer_loop(redis: Redis, http: httpx.AsyncClient, shutdown: asyncio.Event) -> None:
    while not shutdown.is_set():
        raw = await redis.brpop("agentjudge:runs", timeout=2)
        if not raw:
            continue

        payload = json.loads(raw[1])
        run_id = payload["run_id"]
        rubric_id = payload["rubric_id"]
        trace_ids: list[str] = payload["trace_ids"]
        judge_cfg = JudgeConfig(**payload["judge_config"])

        log.info("run_received", run_id=run_id, traces=len(trace_ids))

        try:
            rubric_resp = await http.get(f"{settings.BACKEND_URL}/api/v1/rubrics/{rubric_id}")
            rubric_resp.raise_for_status()
            rubric_data = rubric_resp.json()
            rubric = Rubric(
                name=rubric_data["name"],
                criteria=[Criterion(**c) for c in rubric_data["criteria"]],
            )
        except Exception as e:
            log.error("rubric_fetch_failed", run_id=run_id, error=str(e))
            continue

        evals_resp = await http.get(f"{settings.BACKEND_URL}/api/v1/runs/{run_id}/evaluations")
        evals_resp.raise_for_status()
        evaluations = evals_resp.json()
        eval_map = {e["trace_id"]: e["id"] for e in evaluations}

        await asyncio.gather(*[
            _evaluate_one(http, redis, run_id, trace_id, eval_map.get(trace_id), rubric, judge_cfg)
            for trace_id in trace_ids
        ])


async def _evaluate_one(
    http: httpx.AsyncClient,
    redis: Redis,
    run_id: str,
    trace_id: str,
    evaluation_id: str | None,
    rubric: Rubric,
    config: JudgeConfig,
) -> None:
    if not evaluation_id:
        log.warning("no_evaluation_record", trace_id=trace_id)
        return

    try:
        trace_resp = await http.get(f"{settings.BACKEND_URL}/api/v1/traces/{trace_id}")
        trace_resp.raise_for_status()
        trace = Trace.model_validate(trace_resp.json())

        config_with_keys = config.model_copy(update={
            "api_key": settings.ANTHROPIC_API_KEY if config.provider == "anthropic" else settings.OPENAI_API_KEY
        })
        result = await evaluate(trace, rubric, config_with_keys)

        await http.patch(
            f"{settings.BACKEND_URL}/api/v1/runs/{run_id}/evaluations/{evaluation_id}",
            json={
                "scores": [s.model_dump() for s in result.scores],
                "overall_score": result.overall_score,
                "passed": result.passed,
                "reasoning": result.reasoning,
                "status": "completed",
            },
        )
        log.info("evaluation_done", trace_id=trace_id, score=result.overall_score)

    except Exception as e:
        log.error("evaluation_failed", trace_id=trace_id, error=str(e))
        await http.patch(
            f"{settings.BACKEND_URL}/api/v1/runs/{run_id}/evaluations/{evaluation_id}",
            json={"error": str(e), "status": "failed"},
        )
