"""add_aum_to_institutions

Revision ID: a1b2c3d4e5f6
Revises: 483ddf2ccfc5
Create Date: 2025-12-18 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '483ddf2ccfc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add aum column to institutions table
    op.add_column('institutions', sa.Column('aum', sa.BigInteger(), nullable=True, comment='Assets Under Management in USD'))
    
    # Update AUM values for popular institutions (approximate values in USD)
    op.execute("""
        UPDATE institutions 
        SET aum = CASE 
            WHEN name ILIKE '%Berkshire Hathaway%' THEN 350000000000
            WHEN name ILIKE '%Bridgewater%' THEN 125000000000
            WHEN name ILIKE '%Citadel%' THEN 50000000000
            WHEN name ILIKE '%Renaissance Technologies%' THEN 130000000000
            WHEN name ILIKE '%Two Sigma%' THEN 60000000000
            WHEN name ILIKE '%D.E. Shaw%' THEN 60000000000
            WHEN name ILIKE '%AQR%' THEN 90000000000
            WHEN name ILIKE '%Millennium%' THEN 58000000000
            WHEN name ILIKE '%Baupost%' THEN 31000000000
            WHEN name ILIKE '%Tiger Global%' THEN 50000000000
            WHEN name ILIKE '%Point72%' THEN 26000000000
            WHEN name ILIKE '%Elliott Management%' THEN 55000000000
            WHEN name ILIKE '%Third Point%' THEN 14000000000
            WHEN name ILIKE '%Pershing Square%' THEN 18000000000
            WHEN name ILIKE '%Viking Global%' THEN 42000000000
            WHEN name ILIKE '%Appaloosa%' THEN 8000000000
            WHEN name ILIKE '%Lone Pine%' THEN 23000000000
            WHEN name ILIKE '%Coatue%' THEN 25000000000
            WHEN name ILIKE '%Soros%' THEN 8500000000
            WHEN name ILIKE '%Icahn%' THEN 23000000000
            ELSE NULL
        END
        WHERE aum IS NULL
    """)


def downgrade() -> None:
    op.drop_column('institutions', 'aum')

