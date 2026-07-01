from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ContentSchema(BaseModel):
    content: str
    content_type: Literal["text", "json", "json_rpc"] = "text"


class AgentInfoSchema(BaseModel):
    name: str | None = None
    model: str | None = None
    role: str | None = None


class SpanSchema(BaseModel):
    id: str
    parent_id: str | None = None
    type: Literal["llm", "tool", "handoff", "agent"]
    agent: AgentInfoSchema | None = None
    input: ContentSchema
    output: ContentSchema | None = None
    reasoning: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class TraceCreate(BaseModel):
    input: ContentSchema
    expected: ContentSchema | None = None
    spans: list[SpanSchema] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class TraceResponse(BaseModel):
    id: str
    input: ContentSchema
    expected: ContentSchema | None
    spans: list[SpanSchema]
    metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}
