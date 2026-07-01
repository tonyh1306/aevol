from __future__ import annotations

import json
import os

import openai

from agentjudge.providers.anthropic import _weighted_average
from agentjudge.providers.base import JudgeProvider, build_judge_prompt
from agentjudge.schema import CriterionScore, EvaluationResult, JudgeConfig, Rubric, Trace


class OpenAIJudge(JudgeProvider):
    async def evaluate(self, trace: Trace, rubric: Rubric, config: JudgeConfig) -> EvaluationResult:
        client = openai.AsyncOpenAI(api_key=config.api_key or os.environ.get("OPENAI_API_KEY"))
        prompt = build_judge_prompt(trace, rubric)

        response = await client.chat.completions.create(
            model=config.model,
            temperature=config.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )

        data = json.loads(response.choices[0].message.content)
        scores = [CriterionScore(**s) for s in data["scores"]]
        overall = _weighted_average(scores, rubric)

        return EvaluationResult(
            trace_id=trace.id,
            scores=scores,
            overall_score=overall,
            passed=overall >= 0.7,
            reasoning=data.get("reasoning", ""),
        )
