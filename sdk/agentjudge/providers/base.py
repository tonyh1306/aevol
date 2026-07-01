from __future__ import annotations

from abc import ABC, abstractmethod

from agentjudge.schema import EvaluationResult, JudgeConfig, Rubric, Span, Trace


class JudgeProvider(ABC):
    @abstractmethod
    async def evaluate(self, trace: Trace, rubric: Rubric, config: JudgeConfig) -> EvaluationResult:
        ...


def render_trace(trace: Trace) -> str:
    span_index = {s.id: s for s in trace.spans}
    children: dict[str | None, list[Span]] = {}
    for span in trace.spans:
        children.setdefault(span.parent_id, []).append(span)

    lines: list[str] = []

    def render_span(span: Span, depth: int) -> None:
        indent = "  " * depth
        agent_label = ""
        if span.agent:
            parts = [p for p in [span.agent.name, span.agent.model, span.agent.role] if p]
            if parts:
                agent_label = f" ({', '.join(parts)})"
        lines.append(f"{indent}[{span.type}]{agent_label}")
        lines.append(f"{indent}  input ({span.input.content_type}): {span.input.content}")
        if span.reasoning:
            lines.append(f"{indent}  reasoning: {span.reasoning}")
        if span.output:
            lines.append(f"{indent}  output ({span.output.content_type}): {span.output.content}")
        if span.error:
            lines.append(f"{indent}  error: {span.error}")
        for child in children.get(span.id, []):
            render_span(child, depth + 1)

    lines.append(f"input ({trace.input.content_type}): {trace.input.content}")
    if trace.expected:
        lines.append(f"expected ({trace.expected.content_type}): {trace.expected.content}")
    lines.append("")
    lines.append("execution trace:")
    for root_span in children.get(None, []):
        render_span(root_span, 0)

    return "\n".join(lines)


def build_judge_prompt(trace: Trace, rubric: Rubric) -> str:
    trace_text = render_trace(trace)
    criteria_text = "\n".join(
        f"{i + 1}. {c.name} (weight: {c.weight})\n   {c.description}"
        for i, c in enumerate(rubric.criteria)
    )
    criterion_names = [c.name for c in rubric.criteria]
    return f"""You are evaluating an AI agent's execution trace against a rubric.

## Trace

{trace_text}

## Rubric: {rubric.name}

{criteria_text}

## Instructions

Score each criterion from 0.0 (completely failed) to 1.0 (perfect). Be precise and critical.

Return ONLY valid JSON with no additional text:
{{
  "scores": [
    {{"criterion": "<name>", "score": <0.0-1.0>, "reasoning": "<one sentence>"}}
  ],
  "reasoning": "<overall assessment in 1-2 sentences>"
}}

Criteria to score: {criterion_names}"""
