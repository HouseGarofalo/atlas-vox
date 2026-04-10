"""Add system_settings table.

Revision ID: 001_add_system_settings
Revises: None
Create Date: 2026-04-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "001_add_system_settings"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("key", sa.String(100), nullable=False, index=True),
        sa.Column("value", sa.Text, nullable=False, server_default=""),
        sa.Column("value_type", sa.String(20), nullable=False, server_default="string"),
        sa.Column("is_secret", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("category", "key", name="uq_system_settings_category_key"),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
