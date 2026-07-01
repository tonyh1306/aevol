from __future__ import annotations

import json
import os

import anthropic

from agentjudge.providers.base import JudgeProvider, build_judge_prompt
from agentjudge.schema import CriterionScore, EvaluationResult, JudgeConfig, Rubric, Trace


class AnthropicJudge(JudgeProvider):
    async def evaluate(self, trace: Trace, rubric: Rubric, config: JudgeConfig) -> EvaluationResult:
        client = anthropic.AsyncAnthropic(api_key=config.api_key or os.environ.get("ANTHROPIC_API_KEY"))
        prompt = build_judge_prompt(trace, rubric)

        message = await client.messages.create(
            model=config.model,
            max_tokens=1024,
            temperature=config.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        # strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)
        scores = [CriterionScore(**s) for s in data["scores"]]
        overall = _weighted_average(scores, rubric)

        return EvaluationResult(
            trace_id=trace.id,
            scores=scores,
            overall_score=overall,
            passed=overall >= 0.7,
            reasoning=data.get("reasoning", ""),
        )


def _weighted_average(scores: list[CriterionScore], rubric: Rubric) -> float:
    weight_map = {c.name: c.weight for c in rubric.criteria}
    total_weight = sum(weight_map.get(s.criterion, 1.0) for s in scores)
    if total_weight == 0:
        return 0.0
    return sum(s.score * weight_map.get(s.criterion, 1.0) for s in scores) / total_weight
