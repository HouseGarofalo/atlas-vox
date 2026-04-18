"""Add quality_wer column to synthesis_history (SL-28)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-18 18:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("synthesis_history") as batch_op:
        batch_op.add_column(sa.Column("quality_wer", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("synthesis_history") as batch_op:
        batch_op.drop_column("quality_wer")
