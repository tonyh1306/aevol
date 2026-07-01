from __future__ import annotations

from agentjudge.schema import EvaluationResult, JudgeConfig, Rubric, Trace


async def evaluate(trace: Trace, rubric: Rubric, config: JudgeConfig | None = None) -> EvaluationResult:
    if config is None:
        config = JudgeConfig()

    if config.provider == "anthropic":
        from agentjudge.providers.anthropic import AnthropicJudge
        return await AnthropicJudge().evaluate(trace, rubric, config)
    elif config.provider == "openai":
        from agentjudge.providers.openai import OpenAIJudge
        return await OpenAIJudge().evaluate(trace, rubric, config)
    else:
        raise ValueError(f"unknown provider: {config.provider}")
