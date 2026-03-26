"""stub for missing migration

Revision ID: c0ea9b20ceed
Revises: ba41ddde8ba7
Create Date: 2026-03-24 00:00:00.000000
"""
from alembic import op

revision = 'c0ea9b20ceed'
down_revision = 'ba41ddde8ba7'
branch_labels = None
depends_on = None

def upgrade():
    pass  # эта миграция уже была применена, просто заглушка

def downgrade():
    pass