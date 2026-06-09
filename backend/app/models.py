from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class ExpenseCategory(StrEnum):
    FOOD = "food"
    HOTEL = "hotel"
    TRANSPORTATION = "transportation"
    GAS = "gas"
    TICKETS = "tickets"
    SHOPPING = "shopping"
    OTHER = "other"


class ExpenseType(StrEnum):
    SHARED = "shared"
    PERSONAL = "personal"


class Participant(BaseModel):
    id: str
    name: str


class Expense(BaseModel):
    id: str
    trip_id: str
    title: str
    amount: float = Field(gt=0)
    paid_by: str
    split_among: list[str] = Field(min_length=1)
    expense_type: ExpenseType = ExpenseType.SHARED
    category: ExpenseCategory
    date: str
    currency: Optional[str] = None
    note: Optional[str] = None
    created_at: str
    updated_at: str


class Trip(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: Optional[str] = None
    participants: list[Participant] = Field(default_factory=list)
    expenses: list[Expense] = Field(default_factory=list)
    created_at: str
    updated_at: str


class DataStore(BaseModel):
    trips: list[Trip] = Field(default_factory=list)
