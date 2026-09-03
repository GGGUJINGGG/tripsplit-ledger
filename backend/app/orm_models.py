from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    memberships: Mapped[list[TripMember]] = relationship(
        back_populates="user",
    )


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship()


class PasswordResetToken(TimestampMixin, Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship()


class MemberRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class Trip(TimestampMixin, Base):
    __tablename__ = "trips"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    members: Mapped[list[TripMember]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    expenses: Mapped[list[Expense]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )


class TripMember(TimestampMixin, Base):
    __tablename__ = "trip_members"
    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            "user_id",
            name="uq_trip_members_trip_id_user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(
            MemberRole,
            name="member_role",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=MemberRole.MEMBER,
        nullable=False,
    )

    trip: Mapped[Trip] = relationship(
        back_populates="members",
    )
    user: Mapped[User | None] = relationship(
        back_populates="memberships",
    )
    paid_expenses: Mapped[list[Expense]] = relationship(
        back_populates="paid_by",
        foreign_keys="Expense.paid_by_id",
    )
    expense_shares: Mapped[list[ExpenseShare]] = relationship(
        back_populates="member",
    )


class ExpenseType(StrEnum):
    SHARED = "shared"
    PERSONAL = "personal"


class ExpenseCategory(StrEnum):
    FOOD = "food"
    HOTEL = "hotel"
    TRANSPORTATION = "transportation"
    GAS = "gas"
    TICKETS = "tickets"
    SHOPPING = "shopping"
    OTHER = "other"


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint(
            "amount_cents > 0",
            name="ck_expenses_amount_cents_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paid_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    expense_type: Mapped[ExpenseType] = mapped_column(
        Enum(
            ExpenseType,
            name="expense_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=ExpenseType.SHARED,
        nullable=False,
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(
            ExpenseCategory,
            name="expense_category",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        nullable=False,
    )
    expense_date: Mapped[date] = mapped_column(
        "date",
        Date,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    trip: Mapped[Trip] = relationship(
        back_populates="expenses",
    )
    paid_by: Mapped[TripMember] = relationship(
        back_populates="paid_expenses",
        foreign_keys=[paid_by_id],
    )
    shares: Mapped[list[ExpenseShare]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan",
    )

    @property
    def amount(self) -> float:
        return round(self.amount_cents / 100, 2)

    @property
    def split_among(self) -> list[UUID]:
        return [
            share.member_id
            for share in sorted(
                self.shares,
                key=lambda item: str(item.member_id),
            )
        ]

    @property
    def date(self) -> date:
        return self.expense_date

class ExpenseShare(TimestampMixin, Base):
    __tablename__ = "expense_shares"
    __table_args__ = (
        UniqueConstraint(
            "expense_id",
            "member_id",
            name="uq_expense_shares_expense_id_member_id",
        ),
        CheckConstraint(
            "amount_cents >= 0",
            name="ck_expense_shares_amount_cents_nonnegative",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    expense_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    expense: Mapped[Expense] = relationship(
        back_populates="shares",
    )
    member: Mapped[TripMember] = relationship(
        back_populates="expense_shares",
    )