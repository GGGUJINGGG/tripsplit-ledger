from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models import ExpenseCategory, ExpenseType


class TripCreate(BaseModel):
    name: str = Field(min_length=1)
    start_date: date
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def end_date_must_not_precede_start_date(self) -> "TripCreate":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class TripUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def end_date_must_not_precede_start_date(self) -> "TripUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class ParticipantCreate(BaseModel):
    name: str = Field(min_length=1)


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1)
    amount: float = Field(gt=0)
    paid_by: str
    split_among: list[str] = Field(min_length=1)
    expense_type: ExpenseType = ExpenseType.SHARED
    category: ExpenseCategory
    date: str
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    note: Optional[str] = None


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    amount: Optional[float] = Field(default=None, gt=0)
    paid_by: Optional[str] = None
    split_among: Optional[list[str]] = Field(default=None, min_length=1)
    expense_type: Optional[ExpenseType] = None
    category: Optional[ExpenseCategory] = None
    date: Optional[str] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    note: Optional[str] = None


class CategorySpending(BaseModel):
    category: ExpenseCategory
    amount: float


class DailySpending(BaseModel):
    date: str
    amount: float


class PersonAmount(BaseModel):
    participant_id: str
    name: str
    amount: float


class PersonBalance(BaseModel):
    participant_id: str
    name: str
    balance: float


class DashboardSummary(BaseModel):
    total_trip_spending: float
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


class SettlementSummary(BaseModel):
    settlements: list[Settlement]
