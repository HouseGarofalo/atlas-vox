"""index api_keys.key_prefix for MCP auth lookups (P1-10)

MCP authentication now looks up keys by their 12-char prefix and verifies
exactly one Argon2 hash.  An index on ``key_prefix`` makes the lookup
O(log n) instead of a full scan and is required for bounded auth latency.

Revision ID: b7c8d9e0f1a2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-18 13:47:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_api_keys_key_prefix",
        "api_keys",
        ["key_prefix"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
