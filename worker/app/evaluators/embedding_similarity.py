from app.evaluators.base import EvaluationResult, EvaluatorBase, NonRetryableError
from app.registry import register


@register("embedding_similarity")
class EmbeddingSimilarityEvaluator(EvaluatorBase):
    name = "embedding_similarity"

    async def evaluate(self, payload: dict) -> EvaluationResult:
        input_data = payload.get("input_data", {})
        expected = payload.get("expected_output")
        config = payload.get("config", {})

        prediction = input_data.get("prediction") or input_data.get("output") or ""
        if expected is None:
            raise NonRetryableError("No expected output for embedding similarity.")

        if isinstance(expected, dict):
            expected_str = expected.get("answer") or str(expected)
        else:
            expected_str = str(expected)

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([prediction, expected_str])
            similarity = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        except Exception as e:
            raise NonRetryableError(f"Embedding computation failed: {e}")

        threshold = config.get("threshold", 0.5)
        return EvaluationResult(
            output={"prediction": prediction, "expected": expected_str},
            metrics={
                "cosine_similarity": similarity,
                "accuracy": 1.0 if similarity >= threshold else 0.0,
            },
        )
