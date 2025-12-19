"""Add CWV data column to pages

Revision ID: 002
Revises: 001
Create Date: 2024-12-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cwv_data column to pages table
    op.add_column('pages', sa.Column('cwv_data', JSONB, nullable=True))


def downgrade() -> None:
    # Remove cwv_data column from pages table
    op.drop_column('pages', 'cwv_data')

