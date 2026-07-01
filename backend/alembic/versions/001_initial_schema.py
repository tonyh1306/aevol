"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rubrics",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("criteria", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "traces",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("input", JSONB(), nullable=False),
        sa.Column("expected", JSONB()),
        sa.Column("spans", JSONB(), nullable=False, server_default="[]"),
        sa.Column("metadata", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "runs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rubric_id", UUID(as_uuid=False), sa.ForeignKey("rubrics.id")),
        sa.Column("judge_config", JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("total", sa.Integer(), server_default="0"),
        sa.Column("completed", sa.Integer(), server_default="0"),
        sa.Column("failed", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=False), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("trace_id", UUID(as_uuid=False), sa.ForeignKey("traces.id"), nullable=False),
        sa.Column("scores", JSONB()),
        sa.Column("overall_score", sa.Float()),
        sa.Column("passed", sa.Boolean()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_evaluations_run_id", "evaluations", ["run_id"])
    op.create_index("ix_evaluations_trace_id", "evaluations", ["trace_id"])
    op.create_index("ix_runs_status", "runs", ["status"])


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("runs")
    op.drop_table("traces")
    op.drop_table("rubrics")
