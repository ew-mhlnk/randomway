"""Fix giveaway dates nullable

Revision ID: a1b2c3d4e5f6
Revises: 3ba89ddc3c43
Create Date: 2026-03-20 12:00:00.000000

Причина: start_date и end_date должны быть nullable — черновик розыгрыша
создаётся до того, как пользователь доходит до шага выбора дат (шаг 9).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3ba89ddc3c43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('giveaways', 'start_date',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True)
    op.alter_column('giveaways', 'end_date',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True)


def downgrade() -> None:
    # Внимание: откат сделает колонки NOT NULL.
    # Перед откатом убедитесь, что нет строк с NULL значениями.
    op.alter_column('giveaways', 'end_date',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False)
    op.alter_column('giveaways', 'start_date',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False)
