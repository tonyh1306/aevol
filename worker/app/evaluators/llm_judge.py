import re
import time

import structlog

from app.config import settings
from app.evaluators.base import EvaluationResult, EvaluatorBase, NonRetryableError, RetryableError
from app.registry import register

log = structlog.get_logger()

JUDGE_PROMPT = """You are an expert evaluator. Given a question, a reference answer, and a model's response,
evaluate the model's response on the following criteria: {criteria}.

For each criterion, provide a score from 0.0 to 1.0.

Question: {question}
Reference Answer: {reference}
Model Response: {response}

Respond in JSON format only:
{{"scores": {{"criterion_name": score, ...}}, "overall": 0.0, "reasoning": "brief explanation"}}"""


@register("llm_judge")
class LLMJudgeEvaluator(EvaluatorBase):
    name = "llm_judge"

    async def evaluate(self, payload: dict) -> EvaluationResult:
        config = payload.get("config", {})
        input_data = payload.get("input_data", {})
        expected = payload.get("expected_output")

        model_name = config.get("model_name") or config.get("model", "claude-haiku-4-5-20251001")
        judge_model = config.get("judge_model", "claude-haiku-4-5-20251001")
        criteria = config.get("criteria", ["correctness", "relevance"])
        system_prompt = config.get("system_prompt", "You are a helpful assistant.")

        question = input_data.get("question") or input_data.get("prompt") or str(input_data)
        context = input_data.get("context", "")

        # Step 1: Run the model under test
        t0 = time.monotonic()
        try:
            model_response, prompt_tokens, completion_tokens, cost = await _call_model(
                model_name, system_prompt, question, context, config
            )
        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "529" in err_str or "overloaded" in err_str.lower():
                raise RetryableError(f"Rate limit / overload: {err_str}")
            raise NonRetryableError(f"Model call failed: {err_str}")

        model_latency = int((time.monotonic() - t0) * 1000)

        # Step 2: Judge the response
        reference = str(expected) if expected else "Not provided"
        judge_prompt = JUDGE_PROMPT.format(
            criteria=", ".join(criteria),
            question=question,
            reference=reference,
            response=model_response,
        )

        try:
            judge_response, _, _, judge_cost = await _call_model(
                judge_model, "You are an expert evaluator. Respond only in valid JSON.", judge_prompt, "", config
            )
            scores = _parse_judge_response(judge_response, criteria)
        except Exception as e:
            log.warning("judge_failed", error=str(e))
            scores = {"accuracy": 0.0}
            judge_cost = 0.0

        total_cost = cost + judge_cost
        return EvaluationResult(
            output={"response": model_response, "judge_response": judge_response},
            metrics={
                "latency_ms": float(model_latency),
                "cost_usd": total_cost,
                **scores,
            },
            cost_usd=total_cost,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


async def _call_model(
    model: str, system: str, user_msg: str, context: str, config: dict
) -> tuple[str, int, int, float]:
    full_message = f"{context}\n\n{user_msg}".strip() if context else user_msg
    max_tokens = config.get("max_tokens", 1024)
    temperature = config.get("temperature", 0.0)

    if "claude" in model.lower():
        import anthropic
        if not settings.ANTHROPIC_API_KEY:
            raise NonRetryableError("ANTHROPIC_API_KEY not set")
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": full_message}],
        )
        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = _estimate_anthropic_cost(model, input_tokens, output_tokens)
        return text, input_tokens, output_tokens, cost
    else:
        import openai
        if not settings.OPENAI_API_KEY:
            raise NonRetryableError("OPENAI_API_KEY not set")
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": full_message}],
        )
        text = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = _estimate_openai_cost(model, input_tokens, output_tokens)
        return text, input_tokens, output_tokens, cost


def _parse_judge_response(response: str, criteria: list[str]) -> dict[str, float]:
    import json
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group())
            scores = data.get("scores", {})
            overall = data.get("overall", sum(scores.values()) / len(scores) if scores else 0.0)
            return {"accuracy": overall, **{k: float(v) for k, v in scores.items()}}
    except Exception:
        pass
    for crit in criteria:
        match = re.search(rf'{crit}["\s:]+([0-9.]+)', response, re.IGNORECASE)
        if match:
            return {"accuracy": float(match.group(1))}
    return {"accuracy": 0.0}


def _estimate_anthropic_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = {
        "claude-opus-4-8": (0.000015, 0.000075),
        "claude-sonnet-4-6": (0.000003, 0.000015),
        "claude-haiku-4-5-20251001": (0.00000025, 0.00000125),
    }
    rates = pricing.get(model, (0.000003, 0.000015))
    return input_tokens * rates[0] + output_tokens * rates[1]


def _estimate_openai_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = {
        "gpt-4o": (0.000005, 0.000015),
        "gpt-4o-mini": (0.00000015, 0.0000006),
        "gpt-3.5-turbo": (0.0000005, 0.0000015),
    }
    rates = pricing.get(model, (0.000005, 0.000015))
    return input_tokens * rates[0] + output_tokens * rates[1]
