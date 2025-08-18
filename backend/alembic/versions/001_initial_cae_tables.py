"""initial_cae_tables

Revision ID: 001
Revises: 
Create Date: 2025-01-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database setup"""
    # This migration serves as the base for the unified schema
    # The actual tables are created in migration 002
    pass


def downgrade() -> None:
    """Remove initial database setup"""
    pass