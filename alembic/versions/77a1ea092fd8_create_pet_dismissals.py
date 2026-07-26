"""create pet dismissals

Revision ID: 77a1ea092fd8
Revises: 3f98705e9b3d
Create Date: 2026-07-26 18:38:29.962615

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "77a1ea092fd8"
down_revision: str | Sequence[str] | None = "3f98705e9b3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pet_dismissals",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("pet_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "pet_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_table("pet_dismissals")
