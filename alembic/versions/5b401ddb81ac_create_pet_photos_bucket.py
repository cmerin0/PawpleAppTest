"""create pet photos bucket

Revision ID: 5b401ddb81ac
Revises: 50d9f71d1bb6
Create Date: 2026-07-28 18:42:28.585450

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b401ddb81ac"
down_revision: str | Sequence[str] | None = "50d9f71d1bb6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pet_photos",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pet_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("alt_text", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_pet_photos_sort_order_non_negative"),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
        sa.UniqueConstraint("pet_id", "sort_order", name="uq_pet_photos_pet_sort_order"),
    )
    op.create_index(op.f("ix_pet_photos_pet_id"), "pet_photos", ["pet_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pet_photos_pet_id"), table_name="pet_photos")
    op.drop_table("pet_photos")
