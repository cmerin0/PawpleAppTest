"""(07/25/26) - Create Users table

Revision ID: 867ed177127c
Revises: 
Create Date: 2026-07-25 01:15:36.712671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '867ed177127c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto") # Enable the pgcrypto extension in PostgreSQL to allow for UUID generation and cryptographic functions.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")   # Enable the citext extension in PostgreSQL to allow case-insensitive text columns.

    # Creates the users table with the specified columns and constraints, including a unique index on the email column.
    op.create_table('users',
        sa.Column('id', sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column('email', postgresql.CITEXT(), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('is_platform_admin', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
