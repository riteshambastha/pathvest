"""Add strategies and backtests tables (SQLite compatible)

Revision ID: f1a2b3c4d5e6
Revises: 
Create Date: 2025-12-15 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create strategies table
    op.create_table('strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy_config', sa.Text(), nullable=False),  # JSON as TEXT for SQLite
        sa.Column('selected_institutions', sa.Text(), nullable=True),  # JSON array as TEXT
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_strategies_id'), 'strategies', ['id'], unique=False)
    op.create_index(op.f('ix_strategies_created_at'), 'strategies', ['created_at'], unique=False)
    
    # Create backtests table
    op.create_table('backtests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.String(length=50), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='running'),
        sa.Column('execution_time_seconds', sa.Float(), nullable=True),
        sa.Column('start_date', sa.String(length=20), nullable=True),
        sa.Column('end_date', sa.String(length=20), nullable=True),
        sa.Column('initial_capital', sa.Float(), nullable=True),
        sa.Column('final_value', sa.Float(), nullable=True),
        sa.Column('total_return', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('api_calls_made', sa.Integer(), nullable=True),
        sa.Column('stocks_analyzed', sa.Text(), nullable=True),  # JSON array as TEXT
        sa.Column('real_market_data', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('institutional_signals', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('summary_metrics', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('equity_curve', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('trades', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtests_id'), 'backtests', ['id'], unique=False)
    op.create_index(op.f('ix_backtests_backtest_id'), 'backtests', ['backtest_id'], unique=True)
    op.create_index(op.f('ix_backtests_strategy_id'), 'backtests', ['strategy_id'], unique=False)
    op.create_index(op.f('ix_backtests_created_at'), 'backtests', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_backtests_created_at'), table_name='backtests')
    op.drop_index(op.f('ix_backtests_strategy_id'), table_name='backtests')
    op.drop_index(op.f('ix_backtests_backtest_id'), table_name='backtests')
    op.drop_index(op.f('ix_backtests_id'), table_name='backtests')
    op.drop_table('backtests')
    
    op.drop_index(op.f('ix_strategies_created_at'), table_name='strategies')
    op.create_index(op.f('ix_strategies_id'), table_name='strategies')
    op.drop_table('strategies')

