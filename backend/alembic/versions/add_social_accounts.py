"""Add social_accounts table for multi-account Instagram settings

Revision ID: add_social_accounts
Revises: add_audience_profiles
Create Date: 2026-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'add_social_accounts'
down_revision = 'add_audience_profiles'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'social_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('account_type', sa.String(20), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('password_encrypted', sa.Text(), nullable=True),
        sa.Column('totp_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_social_accounts_org_id', 'org_id'),
        sa.Index('ix_social_accounts_platform', 'platform'),
        sa.Index('ix_social_accounts_status', 'status'),
        sa.UniqueConstraint('org_id', 'platform', 'username', name='uq_social_accounts_org_platform_username'),
        schema='public'
    )


def downgrade() -> None:
    op.drop_table('social_accounts', schema='public')