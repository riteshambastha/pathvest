"""add_sec_filings_fetched_column

Revision ID: b7c8d9e0f1a2
Revises: f1a2b3c4d5e6
Create Date: 2025-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add sec_filings_fetched column to backtests table"""
    # Add the new column
    op.add_column('backtests', sa.Column('sec_filings_fetched', sa.Integer(), nullable=True))
    
    # Set default value for existing rows
    op.execute("UPDATE backtests SET sec_filings_fetched = 0 WHERE sec_filings_fetched IS NULL")


def downgrade() -> None:
    """Remove sec_filings_fetched column from backtests table"""
    op.drop_column('backtests', 'sec_filings_fetched')

