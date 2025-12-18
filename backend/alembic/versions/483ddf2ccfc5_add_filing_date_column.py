"""add_filing_date_column

Revision ID: 483ddf2ccfc5
Revises: f1a2b3c4d5e6
Create Date: 2025-12-18 07:38:15.661156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '483ddf2ccfc5'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add filing_date column (nullable first)
    op.add_column('filings', sa.Column('filing_date', sa.Date(), nullable=True))
    
    # Populate filing_date from filed_at for existing rows
    op.execute("""
        UPDATE filings 
        SET filing_date = DATE(filed_at)
        WHERE filing_date IS NULL
    """)
    
    # Now make it NOT NULL
    op.alter_column('filings', 'filing_date', nullable=False)
    
    # Add index for performance
    op.create_index(op.f('ix_filings_filing_date'), 'filings', ['filing_date'], unique=False)


def downgrade() -> None:
    # Remove index and column
    op.drop_index(op.f('ix_filings_filing_date'), table_name='filings')
    op.drop_column('filings', 'filing_date')

