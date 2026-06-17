from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.evaluators.base import EvaluatorBase

_registry: dict[str, type["EvaluatorBase"]] = {}


def register(name: str):
    def decorator(cls):
        _registry[name] = cls
        return cls
    return decorator


def get(name: str) -> "EvaluatorBase":
    if name not in _registry:
        raise ValueError(f"Unknown evaluator: '{name}'. Available: {list(_registry.keys())}")
    return _registry[name]()


def available() -> list[str]:
    return list(_registry.keys())


def load_all() -> None:
    """Import all evaluator modules to trigger @register decorators."""
    import app.evaluators.exact_match  # noqa: F401
    import app.evaluators.embedding_similarity  # noqa: F401
    import app.evaluators.llm_judge  # noqa: F401
    import app.evaluators.agent_trace  # noqa: F401
