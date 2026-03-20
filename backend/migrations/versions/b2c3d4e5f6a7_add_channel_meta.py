"""Add members_count and photo_file_id to channels

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-21 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('members_count', sa.Integer(), nullable=True))
    op.add_column('channels', sa.Column('photo_file_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('channels', 'photo_file_id')
    op.drop_column('channels', 'members_count')
