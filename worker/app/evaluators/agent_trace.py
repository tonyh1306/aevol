import time

import structlog

from app.config import settings
from app.evaluators.base import EvaluationResult, EvaluatorBase, NonRetryableError, RetryableError
from app.registry import register

log = structlog.get_logger()


@register("agent_trace")
class AgentTraceEvaluator(EvaluatorBase):
    """Evaluates multi-step agent runs by capturing and assessing tool-call traces."""
    name = "agent_trace"

    async def evaluate(self, payload: dict) -> EvaluationResult:
        config = payload.get("config", {})
        input_data = payload.get("input_data", {})
        expected = payload.get("expected_output")

        model_name = config.get("model_name", "claude-haiku-4-5-20251001")
        tools = config.get("tools", [])
        max_steps = config.get("max_steps", 10)
        system_prompt = config.get("system_prompt", "You are a helpful assistant with tool access.")

        if not settings.ANTHROPIC_API_KEY:
            raise NonRetryableError("ANTHROPIC_API_KEY not set for agent trace evaluation")

        question = input_data.get("question") or input_data.get("prompt") or str(input_data)

        trace: list[dict] = []
        total_tokens = 0
        total_cost = 0.0
        t0 = time.monotonic()

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

            messages = [{"role": "user", "content": question}]
            final_response = None

            for step in range(max_steps):
                step_start = time.monotonic()
                response = await client.messages.create(
                    model=model_name,
                    max_tokens=config.get("max_tokens", 1024),
                    system=system_prompt,
                    tools=tools,
                    messages=messages,
                )
                step_latency = int((time.monotonic() - step_start) * 1000)
                total_tokens += response.usage.input_tokens + response.usage.output_tokens

                if response.stop_reason == "end_turn":
                    final_response = response.content[0].text if response.content else ""
                    trace.append({
                        "step_index": step,
                        "step_type": "final",
                        "output_data": {"text": final_response},
                        "latency_ms": step_latency,
                        "tokens_used": response.usage.output_tokens,
                    })
                    break

                if response.stop_reason == "tool_use":
                    tool_uses = [b for b in response.content if b.type == "tool_use"]
                    tool_results = []
                    for tool_use in tool_uses:
                        trace.append({
                            "step_index": step,
                            "step_type": "tool_call",
                            "tool_name": tool_use.name,
                            "tool_args": tool_use.input,
                            "latency_ms": step_latency,
                            "tokens_used": response.usage.output_tokens,
                        })
                        # Mock tool execution — real implementations would call actual tools
                        tool_result = _mock_tool_execution(tool_use.name, tool_use.input)
                        trace.append({
                            "step_index": step,
                            "step_type": "tool_result",
                            "tool_name": tool_use.name,
                            "tool_result": tool_result,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": str(tool_result),
                        })

                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "overloaded" in err_str.lower():
                raise RetryableError(f"API overload: {err_str}")
            raise NonRetryableError(f"Agent execution failed: {err_str}")

        total_latency = int((time.monotonic() - t0) * 1000)

        # Evaluate the final response against expected output
        accuracy = 0.0
        if expected and final_response:
            exp_str = str(expected.get("answer", expected)) if isinstance(expected, dict) else str(expected)
            accuracy = 1.0 if exp_str.strip().lower() in final_response.strip().lower() else 0.0

        # Evaluate tool usage correctness
        expected_tools = config.get("expected_tools", [])
        used_tools = [s["tool_name"] for s in trace if s["step_type"] == "tool_call"]
        tool_precision = _compute_tool_precision(used_tools, expected_tools)

        return EvaluationResult(
            output={"final_response": final_response, "tool_calls": used_tools},
            metrics={
                "accuracy": accuracy,
                "tool_precision": tool_precision,
                "latency_ms": float(total_latency),
                "num_steps": float(len([s for s in trace if s["step_type"] == "tool_call"])),
            },
            trace=trace,
            cost_usd=total_cost,
            prompt_tokens=total_tokens,
        )


def _mock_tool_execution(tool_name: str, tool_args: dict) -> dict:
    return {"status": "ok", "result": f"Mock result for {tool_name}({tool_args})"}


def _compute_tool_precision(used: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    correct = sum(1 for t in used if t in expected)
    return correct / len(expected)
