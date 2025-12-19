"""Add candidate_prompts column to pages

Revision ID: 003
Revises: 002
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add candidate_prompts column to pages table
    op.add_column('pages', sa.Column('candidate_prompts', JSONB, nullable=True))


def downgrade() -> None:
    # Remove candidate_prompts column from pages table
    op.drop_column('pages', 'candidate_prompts')

