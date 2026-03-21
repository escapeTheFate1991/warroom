"""Add audience_profiles table for deeper audience intelligence

Revision ID: add_audience_profiles
Revises: 
Create Date: 2026-03-21 00:53:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'add_audience_profiles'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audience_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('profile_url', sa.String(500), nullable=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('followers', sa.Integer(), nullable=True),
        sa.Column('following', sa.Integer(), nullable=True),
        sa.Column('post_count', sa.Integer(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_business', sa.Boolean(), default=False, nullable=False),
        sa.Column('engagement_level', sa.Enum('high', 'medium', 'low', name='engagement_level'), nullable=False, server_default='medium'),
        sa.Column('first_seen_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.Column('interaction_count', sa.Integer(), default=0, nullable=False),
        sa.Column('profile_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_audience_profiles_org_id', 'org_id'),
        sa.Index('ix_audience_profiles_username_platform', 'username', 'platform'),
        sa.Index('ix_audience_profiles_engagement_level', 'engagement_level'),
        sa.Index('ix_audience_profiles_interaction_count', 'interaction_count'),
        sa.UniqueConstraint('org_id', 'username', 'platform', name='uq_audience_profiles_org_username_platform'),
        schema='crm'
    )

    # Add commenter profile columns to competitor_posts
    op.add_column('competitor_posts', 
                  sa.Column('commenter_username', sa.String(255), nullable=True), 
                  schema='crm')
    op.add_column('competitor_posts', 
                  sa.Column('commenter_profile_url', sa.String(500), nullable=True), 
                  schema='crm')
    op.add_column('competitor_posts', 
                  sa.Column('comment_text', sa.Text(), nullable=True), 
                  schema='crm')
    op.add_column('competitor_posts', 
                  sa.Column('comment_likes', sa.Integer(), nullable=True), 
                  schema='crm')
    op.add_column('competitor_posts', 
                  sa.Column('is_reply', sa.Boolean(), default=False, nullable=True), 
                  schema='crm')
    
    # Add indexes for better query performance
    op.create_index('ix_competitor_posts_commenter_username', 'competitor_posts', ['commenter_username'], schema='crm')


def downgrade() -> None:
    op.drop_index('ix_competitor_posts_commenter_username', 'competitor_posts', schema='crm')
    op.drop_column('competitor_posts', 'is_reply', schema='crm')
    op.drop_column('competitor_posts', 'comment_likes', schema='crm')
    op.drop_column('competitor_posts', 'comment_text', schema='crm')
    op.drop_column('competitor_posts', 'commenter_profile_url', schema='crm')
    op.drop_column('competitor_posts', 'commenter_username', schema='crm')
    op.drop_table('audience_profiles', schema='crm')
    op.execute('DROP TYPE IF EXISTS engagement_level')