"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # datasets
    op.create_table(
        "datasets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("row_count", sa.Integer),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_size", sa.BigInteger),
        sa.Column("schema_info", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # experiments
    op.create_table(
        "experiments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("model_name", sa.String(255)),
        sa.Column("prompt_template", sa.Text),
        sa.Column("tags", ARRAY(sa.Text), server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("total_tasks", sa.Integer, server_default="0"),
        sa.Column("completed_tasks", sa.Integer, server_default="0"),
        sa.Column("failed_tasks", sa.Integer, server_default="0"),
    )
    op.create_index("ix_experiments_status", "experiments", ["status"])
    op.create_index("ix_experiments_parent_id", "experiments", ["parent_id"])
    op.create_index("ix_experiments_dataset_id", "experiments", ["dataset_id"])
    op.create_index("ix_experiments_created_at", "experiments", [sa.text("created_at DESC")])

    # workers
    op.create_table(
        "workers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("pid", sa.Integer, nullable=False),
        sa.Column("version", sa.String(50)),
        sa.Column("status", sa.String(50), nullable=False, server_default="idle"),
        sa.Column("current_task_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tasks_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tasks_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_heartbeat", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("registered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("cpu_percent", sa.Float),
        sa.Column("memory_mb", sa.Integer),
        sa.Column("capabilities", ARRAY(sa.Text), server_default="{}"),
    )
    op.create_index("ix_workers_status", "workers", ["status"])
    op.create_index("ix_workers_last_heartbeat", "workers", ["last_heartbeat"])

    # dataset_rows
    op.create_table(
        "dataset_rows",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_index", sa.Integer, nullable=False),
        sa.Column("input_data", JSONB, nullable=False),
        sa.Column("expected", JSONB),
        sa.Column("metadata", JSONB, server_default="{}"),
    )
    op.create_index("ix_dataset_rows_dataset_row", "dataset_rows", ["dataset_id", "row_index"])

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_row_id", sa.BigInteger, sa.ForeignKey("dataset_rows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("worker_id", UUID(as_uuid=True), sa.ForeignKey("workers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("enqueued_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("claimed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("output_data", JSONB),
        sa.Column("error_message", sa.Text),
        sa.Column("error_type", sa.String(255)),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("cost_usd", sa.Numeric(10, 6)),
        sa.Column("config_override", JSONB),
        sa.Column("metadata", JSONB, server_default="{}"),
    )
    op.create_index("ix_tasks_experiment_status", "tasks", ["experiment_id", "status"])
    op.create_index("ix_tasks_status_enqueued", "tasks", ["status", "enqueued_at"])
    op.create_index("ix_tasks_worker_id", "tasks", ["worker_id"])

    # metrics
    op.create_table(
        "metrics",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_metrics_experiment_name", "metrics", ["experiment_id", "name"])
    op.create_index("ix_metrics_task_id", "metrics", ["task_id"])
    op.create_index("ix_metrics_name_experiment", "metrics", ["name", "experiment_id"])

    # agent_traces
    op.create_table(
        "agent_traces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("input_data", JSONB),
        sa.Column("output_data", JSONB),
        sa.Column("tool_name", sa.String(255)),
        sa.Column("tool_args", JSONB),
        sa.Column("tool_result", JSONB),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("error", sa.Text),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_agent_traces_task_step", "agent_traces", ["task_id", "step_index"])

    # failure_clusters
    op.create_table(
        "failure_clusters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_label", sa.String(255), nullable=False),
        sa.Column("error_pattern", sa.Text, nullable=False),
        sa.Column("sample_errors", ARRAY(sa.Text), server_default="{}"),
        sa.Column("task_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("suggestion", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_failure_clusters_experiment_id", "failure_clusters", ["experiment_id"])

    # reports
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("baseline_id", UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("summary", JSONB, nullable=False, server_default="{}"),
        sa.Column("regression_flags", JSONB, server_default="[]"),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("failure_clusters")
    op.drop_table("agent_traces")
    op.drop_table("metrics")
    op.drop_table("tasks")
    op.drop_table("dataset_rows")
    op.drop_table("workers")
    op.drop_table("experiments")
    op.drop_table("datasets")
