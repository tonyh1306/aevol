import uuid
from collections import defaultdict

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.failure_cluster import FailureCluster
from app.models.task import Task

log = structlog.get_logger()

SUGGESTION_TEMPLATES = {
    "TimeoutError": "Consider increasing the model timeout or reducing input length to avoid timeouts.",
    "RateLimitError": "Implement exponential backoff and reduce concurrency to stay within rate limits.",
    "AuthenticationError": "Verify that API keys are correctly set in environment variables.",
    "ValidationError": "Check that input data matches the expected schema for this evaluator.",
    "ConnectionError": "Ensure the model API endpoint is reachable from the worker network.",
    "default": "Review the error patterns and inspect sample inputs to identify the root cause.",
}


async def cluster_failures(db: AsyncSession, experiment_id: uuid.UUID) -> list[FailureCluster]:
    result = await db.execute(
        select(Task.error_type, Task.error_message)
        .where(Task.experiment_id == experiment_id, Task.status.in_(["FAILED", "DEAD"]))
    )
    failures = result.fetchall()

    if not failures:
        return []

    # Delete stale clusters for this experiment
    old = await db.execute(select(FailureCluster).where(FailureCluster.experiment_id == experiment_id))
    for cluster in old.scalars():
        await db.delete(cluster)

    # Group by error_type first
    by_type: dict[str, list[str]] = defaultdict(list)
    for error_type, error_msg in failures:
        key = error_type or "Unknown"
        if error_msg:
            by_type[key].append(error_msg)

    clusters: list[FailureCluster] = []

    for error_type, messages in by_type.items():
        if len(messages) >= 5:
            # Use TF-IDF + KMeans for semantic sub-clustering
            sub_clusters = _tfidf_cluster(messages, n_clusters=min(3, len(messages) // 2))
        else:
            sub_clusters = {error_type: messages}

        for label, msgs in sub_clusters.items():
            suggestion = _get_suggestion(error_type)
            cluster = FailureCluster(
                experiment_id=experiment_id,
                cluster_label=label,
                error_pattern=_extract_pattern(msgs),
                sample_errors=msgs[:5],
                task_count=len(msgs),
                suggestion=suggestion,
            )
            db.add(cluster)
            clusters.append(cluster)

    await db.commit()
    log.info("clusters_computed", experiment_id=str(experiment_id), cluster_count=len(clusters))
    return clusters


def _tfidf_cluster(messages: list[str], n_clusters: int) -> dict[str, list[str]]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans

        vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
        X = vectorizer.fit_transform(messages)
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X)

        result: dict[str, list[str]] = defaultdict(list)
        for msg, label in zip(messages, labels):
            result[f"cluster_{label}"].append(msg)
        return dict(result)
    except Exception:
        return {"cluster_0": messages}


def _extract_pattern(messages: list[str]) -> str:
    if not messages:
        return ""
    # Use the most common prefix as the pattern
    words = messages[0].split()[:8]
    return " ".join(words)


def _get_suggestion(error_type: str) -> str:
    for key, suggestion in SUGGESTION_TEMPLATES.items():
        if key.lower() in error_type.lower():
            return suggestion
    return SUGGESTION_TEMPLATES["default"]


async def get_clusters(db: AsyncSession, experiment_id: uuid.UUID) -> list[FailureCluster]:
    result = await db.execute(
        select(FailureCluster)
        .where(FailureCluster.experiment_id == experiment_id)
        .order_by(FailureCluster.task_count.desc())
    )
    return list(result.scalars())
