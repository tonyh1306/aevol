from app.evaluators.base import EvaluationResult, EvaluatorBase
from app.registry import register


@register("exact_match")
class ExactMatchEvaluator(EvaluatorBase):
    name = "exact_match"

    async def evaluate(self, payload: dict) -> EvaluationResult:
        input_data = payload.get("input_data", {})
        expected = payload.get("expected_output")
        config = payload.get("config", {})

        prediction = input_data.get("prediction") or input_data.get("output") or ""
        if expected is None:
            return EvaluationResult(
                output={"prediction": prediction},
                metrics={"accuracy": 0.0},
                error="No expected output provided",
            )

        if isinstance(expected, dict):
            expected_str = expected.get("answer") or str(expected)
        else:
            expected_str = str(expected)

        normalize = config.get("normalize", True)
        if normalize:
            prediction = prediction.strip().lower()
            expected_str = expected_str.strip().lower()

        match = prediction == expected_str
        partial = _compute_token_overlap(prediction, expected_str)

        return EvaluationResult(
            output={"prediction": prediction, "expected": expected_str},
            metrics={
                "accuracy": 1.0 if match else 0.0,
                "token_overlap": partial,
            },
        )


def _compute_token_overlap(pred: str, expected: str) -> float:
    pred_tokens = set(pred.split())
    exp_tokens = set(expected.split())
    if not exp_tokens:
        return 0.0
    return len(pred_tokens & exp_tokens) / len(exp_tokens)
