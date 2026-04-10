from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '79545805f81a'
down_revision: Union[str, Sequence[str], None] = 'c0ea9b20ceed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('participants',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('giveaway_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('referral_code', sa.String(length=20), nullable=False),
        sa.Column('referred_by', sa.String(length=20), nullable=True),
        sa.Column('invite_count', sa.Integer(), nullable=False),
        sa.Column('has_boosted', sa.Boolean(), nullable=False),
        sa.Column('story_clicks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_winner', sa.Boolean(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['giveaway_id'], ['giveaways.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participants_giveaway_id'), 'participants',['giveaway_id'], unique=False)
    op.create_index(op.f('ix_participants_referral_code'), 'participants', ['referral_code'], unique=True)
    op.create_index(op.f('ix_participants_user_id'), 'participants', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_participants_user_id'), table_name='participants')
    op.drop_index(op.f('ix_participants_referral_code'), table_name='participants')
    op.drop_index(op.f('ix_participants_giveaway_id'), table_name='participants')
    op.drop_table('participants')