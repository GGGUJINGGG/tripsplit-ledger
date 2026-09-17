from __future__ import annotations
from datetime import date as DataType, datetime
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.currencies import VALID_CURRENCY_CODES
from app.orm_models import ExpenseCategory, ExpenseType, MemberRole, PaymentStatus


def _validate_currency_code(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value

    normalized = value.upper()
    if normalized not in VALID_CURRENCY_CODES:
        raise ValueError(f"Unknown currency code: {value}")
    return normalized


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12, max_length=128)

class TripCreate(BaseModel):
    name: str = Field(min_length=1)
    start_date: DataType
    end_date: Optional[DataType] = None

    @model_validator(mode="after")
    def end_date_must_not_precede_start_date(self) -> "TripCreate":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class TripUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    start_date: Optional[DataType] = None
    end_date: Optional[DataType] = None

    @model_validator(mode="after")
    def end_date_must_not_precede_start_date(self) -> "TripUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(validation_alias="display_name")
    user_id: Optional[UUID] = None
    role: MemberRole


class PendingInvitation(BaseModel):
    id: UUID
    trip_id: UUID
    trip_name: str
    invited_at: datetime


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    start_date: DataType
    end_date: Optional[DataType]
    participants: list[ParticipantRead] = Field(
        default_factory=list,
        validation_alias="members",
    )
    expenses: list[ExpenseRead] = Field(default_factory=list)
    payments: list[PaymentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ParticipantCreate(BaseModel):
    name: str = Field(min_length=1)


class MemberInvite(BaseModel):
    email: EmailStr


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1)
    amount: float = Field(gt=0)
    paid_by: UUID
    split_among: list[UUID] = Field(min_length=1)
    expense_type: ExpenseType = ExpenseType.SHARED
    category: ExpenseCategory
    date: DataType
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    note: Optional[str] = None

    _validate_currency = field_validator("currency")(
        _validate_currency_code
    )


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    amount: Optional[float] = Field(default=None, gt=0)
    paid_by: Optional[UUID] = None
    split_among: Optional[list[UUID]] = Field(default=None, min_length=1)
    expense_type: Optional[ExpenseType] = None
    category: Optional[ExpenseCategory] = None
    date: Optional[DataType] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    note: Optional[str] = None

    _validate_currency = field_validator("currency")(
        _validate_currency_code
    )


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    trip_id: UUID
    title: str
    amount: float
    paid_by: UUID = Field(validation_alias="paid_by_id")
    split_among: list[UUID]
    expense_type: ExpenseType
    category: ExpenseCategory
    date: DataType
    currency: str
    note: Optional[str]
    created_at: datetime
    updated_at: datetime


class ExpensePage(BaseModel):
    items: list[ExpenseRead]
    total: int
    limit: int
    offset: int


class PaymentCreate(BaseModel):
    from_participant: UUID
    to_participant: UUID
    amount: float = Field(gt=0)
    date: DataType
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    note: Optional[str] = None

    _validate_currency = field_validator("currency")(
        _validate_currency_code
    )

    @field_validator("date")
    @classmethod
    def date_must_not_be_in_the_future(cls, value: DataType) -> DataType:
        if value > DataType.today():
            raise ValueError("date cannot be in the future")
        return value

    @model_validator(mode="after")
    def from_and_to_must_differ(self) -> "PaymentCreate":
        if self.from_participant == self.to_participant:
            raise ValueError(
                "from_participant and to_participant must be different people"
            )
        return self


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    trip_id: UUID
    from_participant: UUID = Field(validation_alias="from_member_id")
    to_participant: UUID = Field(validation_alias="to_member_id")
    amount: float
    currency: str
    date: DataType
    note: Optional[str]
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class CurrencyAmount(BaseModel):
    currency: str
    amount: float


class CategorySpending(BaseModel):
    category: ExpenseCategory
    currency: str
    amount: float


class DailySpending(BaseModel):
    date: str
    currency: str
    amount: float


class PersonAmount(BaseModel):
    participant_id: str
    name: str
    currency: str
    amount: float


class PersonBalance(BaseModel):
    participant_id: str
    name: str
    currency: str
    balance: float


class DashboardSummary(BaseModel):
    """Every field here is segmented by currency instead of summed
    across them — a trip with both USD and CNY shared expenses gets
    separate entries per currency rather than one meaningless combined
    number. See README's Known Limitations for why: there's still no
    exchange-rate conversion, so summing raw amounts across currencies
    would silently add unrelated units together."""

    total_trip_spending: list[CurrencyAmount]
    spending_by_category: list[CategorySpending]
    spending_by_day: list[DailySpending]
    paid_by_person: list[PersonAmount]
    owed_by_person: list[PersonAmount]
    net_balances: list[PersonBalance]


class Settlement(BaseModel):
    from_participant_id: str
    from_name: str
    to_participant_id: str
    to_name: str
    amount: float
    currency: str


class SettlementSummary(BaseModel):
    settlements: list[Settlement]
