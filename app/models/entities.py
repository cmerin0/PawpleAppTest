from __future__ import annotations  # This import allows for forward references in type hints

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Define an enumeration for the roles a user can have within a shelter.
class ShelterMemberRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"

# Define an enumeration for the lifecycle states of a pet listing.
class PetStatus(StrEnum):
    DRAFT = "draft"
    AVAILABLE = "available"
    PENDING = "pending"
    ADOPTED = "adopted"
    UNAVAILABLE = "unavailable"

# The User model represents a registered user in the application.
class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shelter_membership: Mapped[ShelterMember | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )


# The Shelter model represents a US-based organization that publishes pet listings.
class Shelter(Base):
    __tablename__ = "shelters"
    __table_args__ = (
        CheckConstraint(
            "char_length(state) = 2",
            name="ck_shelters_state_length",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(
        String(160),
        unique=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(CITEXT)
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    members: Mapped[list[ShelterMember]] = relationship(
        back_populates="shelter",
        cascade="all, delete-orphan",
    )

    pets: Mapped[list[Pet]] = relationship(
        back_populates="shelter",
    )


# The ShelterMember model represents a user's role within a shelter,
# linking users to shelters with a specific role (owner, manager, or staff).
class ShelterMember(Base):
    __tablename__ = "shelter_members"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_shelter_members_user",
        ),
    )

    shelter_id: Mapped[UUID] = mapped_column(
        ForeignKey("shelters.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[ShelterMemberRole] = mapped_column(
        Enum(
            ShelterMemberRole,
            name="shelter_member_role",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        default=ShelterMemberRole.STAFF,
        server_default=ShelterMemberRole.STAFF.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    shelter: Mapped[Shelter] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="shelter_membership")

# The Pet model represents a pet listing associated with a shelter, 
# including details such as name, species, breed, and status.
class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        Index(
            "ix_pets_shelter_status",
            "shelter_id",
            "status",
        ),
        Index(
            "ix_pets_available",
            "status",
            postgresql_where=text("status = 'available'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    shelter_id: Mapped[UUID] = mapped_column(
        ForeignKey("shelters.id", ondelete="RESTRICT"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    species: Mapped[str] = mapped_column(String(40))
    breed: Mapped[str | None] = mapped_column(String(100))
    sex: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date)
    size: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PetStatus] = mapped_column(
        Enum(
            PetStatus,
            name="pet_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=PetStatus.DRAFT,
        server_default=PetStatus.DRAFT.value,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    shelter: Mapped[Shelter] = relationship(
        back_populates="pets",
    )