from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ContentType = Literal["text", "json", "json_rpc"]
SpanType = Literal["llm", "tool", "handoff", "agent"]


class Content(BaseModel):
    content: str
    content_type: ContentType = "text"


class AgentInfo(BaseModel):
    name: str | None = None
    model: str | None = None
    role: str | None = None


class Span(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    type: SpanType
    agent: AgentInfo | None = None
    input: Content
    output: Content | None = None
    reasoning: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class Trace(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    input: Content
    expected: Content | None = None
    spans: list[Span] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class Criterion(BaseModel):
    name: str
    description: str
    weight: float = 1.0


class Rubric(BaseModel):
    name: str
    criteria: list[Criterion]


class JudgeConfig(BaseModel):
    provider: Literal["anthropic", "openai"] = "anthropic"
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.0
    api_key: str | None = None


class CriterionScore(BaseModel):
    criterion: str
    score: float
    reasoning: str


class EvaluationResult(BaseModel):
    trace_id: str
    scores: list[CriterionScore]
    overall_score: float
    passed: bool
    reasoning: str
    pass_threshold: float = 0.7
