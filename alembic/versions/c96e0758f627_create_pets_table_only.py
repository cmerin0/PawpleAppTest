"""create pets table only

Revision ID: c96e0758f627
Revises: b42d4134d7c1
Create Date: 2026-07-26 15:21:13.424373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c96e0758f627'
down_revision: Union[str, Sequence[str], None] = 'b42d4134d7c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('pets',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('shelter_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('species', sa.String(length=40), nullable=False),
    sa.Column('breed', sa.String(length=100), nullable=True),
    sa.Column('sex', sa.String(length=20), nullable=True),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('size', sa.String(length=30), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('draft', 'available', 'pending', 'adopted', 'unavailable', name='pet_status', native_enum=False, create_constraint=True), server_default='draft', nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['shelter_id'], ['shelters.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pets_available', 'pets', ['status'], unique=False, postgresql_where=sa.text("status = 'available'"))
    op.create_index(op.f('ix_pets_shelter_id'), 'pets', ['shelter_id'], unique=False)
    op.create_index('ix_pets_shelter_status', 'pets', ['shelter_id', 'status'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_index('ix_pets_shelter_status', table_name='pets')
    op.drop_index(op.f('ix_pets_shelter_id'), table_name='pets')
    op.drop_index('ix_pets_available', table_name='pets', postgresql_where=sa.text("status = 'available'"))
    op.drop_table('pets')
