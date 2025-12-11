"""Initial schema with all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=False),
        sa.Column('role', sa.String(50), default='viewer', nullable=False),
        sa.Column('settings', postgresql.JSONB(), default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_domains', postgresql.JSONB(), default=list),
        sa.Column('crawl_config', postgresql.JSONB(), default=dict),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # CSV Imports table
    op.create_table(
        'csv_imports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), default='pending', nullable=False),
        sa.Column('error_message', sa.String(1024), nullable=True),
        sa.Column('column_mapping', postgresql.JSONB(), default=dict),
        sa.Column('total_rows', sa.Integer(), nullable=True),
        sa.Column('processed_rows', sa.Integer(), default=0),
        sa.Column('failed_rows', sa.Integer(), default=0),
        sa.Column('job_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Crawl Jobs table
    op.create_table(
        'crawl_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), default='pending', nullable=False),
        sa.Column('config', postgresql.JSONB(), default=dict),
        sa.Column('total_urls', sa.Integer(), default=0),
        sa.Column('crawled_urls', sa.Integer(), default=0),
        sa.Column('failed_urls', sa.Integer(), default=0),
        sa.Column('error_message', sa.String(1024), nullable=True),
        sa.Column('errors', postgresql.JSONB(), default=list),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Pages table
    op.create_table(
        'pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('crawl_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crawl_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('canonical_url', sa.String(2048), nullable=True),
        sa.Column('status_code', sa.String(10), nullable=True),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('title', sa.String(512), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('word_count', sa.String(20), nullable=True),
        sa.Column('html_snapshot_path', sa.String(512), nullable=True),
        sa.Column('structured_data', postgresql.JSONB(), default=list),
        sa.Column('mcp_checks', postgresql.JSONB(), default=dict),
        sa.Column('hreflang_tags', postgresql.JSONB(), default=list),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('crawled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_pages_url', 'pages', ['url'])
    op.create_index('ix_pages_project_id', 'pages', ['project_id'])
    
    # Prompts table
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('csv_import_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('csv_imports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('normalized_text', sa.Text(), nullable=True),
        sa.Column('topic', sa.String(255), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('language', sa.String(10), nullable=True),
        sa.Column('popularity_score', sa.Float(), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('visibility_score', sa.Float(), nullable=True),
        sa.Column('intent_label', sa.String(50), default='unknown', nullable=False),
        sa.Column('transaction_score', sa.Float(), default=0.0),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('match_status', sa.String(50), default='pending', nullable=False),
        sa.Column('best_match_score', sa.Float(), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(), default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_prompts_topic', 'prompts', ['topic'])
    op.create_index('ix_prompts_language', 'prompts', ['language'])
    op.create_index('ix_prompts_intent_label', 'prompts', ['intent_label'])
    op.create_index('ix_prompts_match_status', 'prompts', ['match_status'])
    op.create_index('ix_prompts_transaction_score', 'prompts', ['transaction_score'])
    
    # Matches table
    op.create_table(
        'matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('match_type', sa.String(50), default='semantic', nullable=False),
        sa.Column('matched_snippet', sa.Text(), nullable=True),
        sa.Column('rank', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_matches_prompt_id', 'matches', ['prompt_id'])
    op.create_index('ix_matches_page_id', 'matches', ['page_id'])
    op.create_index('ix_matches_similarity_score', 'matches', ['similarity_score'])
    
    # Opportunities table
    op.create_table(
        'opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompts.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('priority_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('popularity_weight', sa.Float(), nullable=True),
        sa.Column('transaction_weight', sa.Float(), nullable=True),
        sa.Column('sentiment_weight', sa.Float(), nullable=True),
        sa.Column('difficulty_weight', sa.Float(), nullable=True),
        sa.Column('difficulty_score', sa.Float(), nullable=True),
        sa.Column('difficulty_factors', postgresql.JSONB(), default=dict),
        sa.Column('recommended_action', sa.String(50), default='other', nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), default='new', nullable=False),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('content_suggestion', postgresql.JSONB(), default=dict),
        sa.Column('related_page_ids', postgresql.JSONB(), default=list),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_opportunities_status', 'opportunities', ['status'])
    op.create_index('ix_opportunities_priority_score', 'opportunities', ['priority_score'])
    op.create_index('ix_opportunities_recommended_action', 'opportunities', ['recommended_action'])


def downgrade() -> None:
    op.drop_table('opportunities')
    op.drop_table('matches')
    op.drop_table('prompts')
    op.drop_table('pages')
    op.drop_table('crawl_jobs')
    op.drop_table('csv_imports')
    op.drop_table('projects')
    op.drop_table('users')

