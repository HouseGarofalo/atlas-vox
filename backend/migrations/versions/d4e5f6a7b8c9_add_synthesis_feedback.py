"""Add synthesis_feedback table (SL-25)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-18 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "synthesis_feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("history_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.String(length=10), nullable=False),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["history_id"], ["synthesis_history.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_synthesis_feedback_history_id"),
        "synthesis_feedback",
        ["history_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_synthesis_feedback_created_at"),
        "synthesis_feedback",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_synthesis_feedback_created_at"),
        table_name="synthesis_feedback",
    )
    op.drop_index(
        op.f("ix_synthesis_feedback_history_id"),
        table_name="synthesis_feedback",
    )
    op.drop_table("synthesis_feedback")
