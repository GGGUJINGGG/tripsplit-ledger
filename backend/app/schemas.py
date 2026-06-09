from typing import Optional

from pydantic import BaseModel, Field

from app.models import ExpenseCategory, ExpenseType


class TripCreate(BaseModel):
    name: str = Field(min_length=1)
    start_date: str
    end_date: Optional[str] = None


class TripUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


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
