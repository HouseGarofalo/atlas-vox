"""widen api_keys.key_prefix to VARCHAR(20)

The endpoint stores the first 12 chars of the raw key (e.g. ``avx_xxxxxxxx``)
but the column was declared ``VARCHAR(10)``. On strict databases (Postgres)
this raised StringDataRightTruncationError on every create.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-15 06:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.alter_column(
            "key_prefix",
            existing_type=sa.String(length=10),
            type_=sa.String(length=20),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.alter_column(
            "key_prefix",
            existing_type=sa.String(length=20),
            type_=sa.String(length=10),
            existing_nullable=False,
        )
