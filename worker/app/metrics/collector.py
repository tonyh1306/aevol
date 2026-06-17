import structlog
import httpx

from app.config import settings
from app.evaluators.base import EvaluationResult

log = structlog.get_logger()


async def push_metrics(
    http_client: httpx.AsyncClient,
    task_id: str,
    experiment_id: str,
    result: EvaluationResult,
    latency_ms: int,
) -> None:
    """POST task result and metrics back to the backend."""
    all_metrics = {
        "latency_ms": float(latency_ms),
        "cost_usd": result.cost_usd,
        **result.metrics,
    }

    task_update = {
        "status": "COMPLETED",
        "output_data": {"output": str(result.output)[:4000] if result.output else None},
        "latency_ms": latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "cost_usd": result.cost_usd,
    }

    try:
        await http_client.patch(
            f"{settings.BACKEND_URL}/api/v1/tasks/{task_id}/result",
            json=task_update,
            timeout=10.0,
        )
    except Exception as e:
        log.warning("task_result_push_failed", task_id=task_id, error=str(e))

    metric_payloads = [
        {"name": k, "value": v, "unit": _infer_unit(k)}
        for k, v in all_metrics.items()
    ]

    try:
        await http_client.post(
            f"{settings.BACKEND_URL}/api/v1/tasks/{task_id}/metrics",
            json={"experiment_id": experiment_id, "metrics": metric_payloads},
            timeout=10.0,
        )
    except Exception as e:
        log.warning("metrics_push_failed", task_id=task_id, error=str(e))

    if result.trace:
        try:
            await http_client.post(
                f"{settings.BACKEND_URL}/api/v1/tasks/{task_id}/traces",
                json={"steps": result.trace},
                timeout=10.0,
            )
        except Exception as e:
            log.warning("trace_push_failed", task_id=task_id, error=str(e))


def _infer_unit(metric_name: str) -> str:
    if "ms" in metric_name or "latency" in metric_name:
        return "ms"
    if "usd" in metric_name or "cost" in metric_name:
        return "usd"
    if "token" in metric_name:
        return "tokens"
    return "score"
