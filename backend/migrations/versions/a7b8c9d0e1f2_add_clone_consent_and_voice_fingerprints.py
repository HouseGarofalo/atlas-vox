"""Add clone_consent and voice_fingerprints tables (SC-44, SC-46)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-18 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Voice clone consent ledger — append-only audit trail.
    op.create_table(
        "clone_consent",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_audio_hash", sa.String(length=64), nullable=False),
        sa.Column("target_profile_id", sa.String(length=36), nullable=False),
        sa.Column("target_provider", sa.String(length=50), nullable=False),
        sa.Column("consent_text", sa.Text(), nullable=False),
        sa.Column(
            "consent_granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("operator_user_id", sa.String(length=200), nullable=False),
        sa.Column("consent_proof_blob", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["target_profile_id"], ["voice_profiles.id"]),
    )
    op.create_index(
        op.f("ix_clone_consent_source_audio_hash"),
        "clone_consent",
        ["source_audio_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_clone_consent_target_profile_id"),
        "clone_consent",
        ["target_profile_id"],
        unique=False,
    )

    # Voice fingerprints — speaker embeddings keyed per sample.
    op.create_table(
        "voice_fingerprints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sample_id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("embedding_json", sa.Text(), nullable=False),
        sa.Column(
            "method",
            sa.String(length=50),
            nullable=False,
            server_default="mfcc_mean",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["audio_samples.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["voice_profiles.id"]),
    )
    op.create_index(
        op.f("ix_voice_fingerprints_sample_id"),
        "voice_fingerprints",
        ["sample_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_voice_fingerprints_profile_id"),
        "voice_fingerprints",
        ["profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_voice_fingerprints_profile_id"),
        table_name="voice_fingerprints",
    )
    op.drop_index(
        op.f("ix_voice_fingerprints_sample_id"),
        table_name="voice_fingerprints",
    )
    op.drop_table("voice_fingerprints")
    op.drop_index(
        op.f("ix_clone_consent_target_profile_id"),
        table_name="clone_consent",
    )
    op.drop_index(
        op.f("ix_clone_consent_source_audio_hash"),
        table_name="clone_consent",
    )
    op.drop_table("clone_consent")
