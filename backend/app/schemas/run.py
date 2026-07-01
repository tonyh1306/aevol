from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class JudgeConfigSchema(BaseModel):
    provider: Literal["anthropic", "openai"] = "anthropic"
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.0


class RunCreate(BaseModel):
    name: str
    rubric_id: str
    trace_ids: list[str]
    judge_config: JudgeConfigSchema = JudgeConfigSchema()


class RunResponse(BaseModel):
    id: str
    name: str
    rubric_id: str | None
    judge_config: JudgeConfigSchema
    status: str
    total: int
    completed: int
    failed: int
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
