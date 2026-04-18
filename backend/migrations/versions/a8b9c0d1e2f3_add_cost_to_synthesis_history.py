"""VQ-39 — add estimated_cost_usd to synthesis_history

Introduces a NULLABLE cost column stamped at synthesis time. Rows written
before this migration stay NULL; aggregation endpoints treat NULL as 0.0.

Revision ID: a8b9c0d1e2f3
Revises: f6a7b8c9d0e1
Create Date: 2026-04-18 17:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("synthesis_history") as batch_op:
        batch_op.add_column(
            sa.Column("estimated_cost_usd", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("synthesis_history") as batch_op:
        batch_op.drop_column("estimated_cost_usd")
