"""add transcript and pronunciation columns to audio_samples

Revision ID: a1b2c3d4e5f6
Revises: 8ac331940296
Create Date: 2026-03-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8ac331940296'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audio_samples', sa.Column('transcript', sa.Text(), nullable=True))
    op.add_column('audio_samples', sa.Column('transcript_source', sa.String(20), nullable=True))
    op.add_column('audio_samples', sa.Column('pronunciation_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('audio_samples', 'pronunciation_json')
    op.drop_column('audio_samples', 'transcript_source')
    op.drop_column('audio_samples', 'transcript')
