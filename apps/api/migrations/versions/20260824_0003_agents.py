"""Add durable agent workflow state.

Revision ID: 20260824_0003
Revises: 20260824_0002
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0003"
down_revision: str | None = "20260824_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("test_runs", sa.Column("active_operation_id", sa.String(36), nullable=True))
    op.add_column(
        "test_runs",
        sa.Column("agent_settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_table(
        "question_evaluation_records",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("test_run_id", sa.String(36), nullable=False),
        sa.Column("question_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "test_run_id", "question_id", name="uq_question_evaluations_test_question"
        ),
    )
    op.create_index(
        "ix_question_evaluations_test_status",
        "question_evaluation_records",
        ["test_run_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_question_evaluations_test_status", table_name="question_evaluation_records"
    )
    op.drop_table("question_evaluation_records")
    op.drop_column("test_runs", "agent_settings")
    op.drop_column("test_runs", "active_operation_id")
