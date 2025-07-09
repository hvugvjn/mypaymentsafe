"""Change images column to JSON

Revision ID: ad64314770f9
Revises: 3afb2b10fd04
Create Date: 2025-07-09 01:21:58.469208
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ad64314770f9'
down_revision = '3afb2b10fd04'
branch_labels = None
depends_on = None

def upgrade():
    op.execute('ALTER TABLE transaction ALTER COLUMN images TYPE JSON USING images::json')

def downgrade():
    op.execute('ALTER TABLE transaction ALTER COLUMN images TYPE TEXT')
