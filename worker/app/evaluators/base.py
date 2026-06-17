from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    output: Any
    metrics: dict[str, float] = field(default_factory=dict)
    trace: list[dict] | None = None
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None


class RetryableError(Exception):
    """Raised for transient errors that should be retried."""
    pass


class NonRetryableError(Exception):
    """Raised for permanent errors — goes straight to DLQ."""
    pass


class EvaluatorBase(ABC):
    name: str

    @abstractmethod
    async def evaluate(self, payload: dict) -> EvaluationResult:
        """Execute evaluation for a single task payload."""
        ...

    def validate_config(self, config: dict) -> None:
        """Raise ValueError if required config keys are missing."""
        pass
