from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth_dependencies import get_current_user
from app.database import get_db
from app.orm_models import (
    Expense,
    ExpenseCategory as DBExpenseCategory,
    ExpenseShare,
    ExpenseType as DBExpenseType,
    Trip,
    TripMember,
    User,
)
from app.routers.trips import find_trip_or_404
from app.schemas import ExpenseCreate, ExpenseRead, ExpenseUpdate, ExpensePage
from app.services.calculations import is_expense_visible, split_cents_evenly


router = APIRouter(
    prefix="/trips/{trip_id}/expenses",
    tags=["expenses"],
)


def amount_to_cents(amount: float) -> int:
    return round(amount * 100)


def find_expense_or_404(
    db: Session,
    trip_id: UUID,
    expense_id: UUID,
    current_user_id: UUID,
) -> Expense:
    statement = (
        select(Expense)
        .options(
            selectinload(Expense.shares),
            selectinload(Expense.paid_by),
        )
        .where(
            Expense.id == expense_id,
            Expense.trip_id == trip_id,
        )
    )
    expense = db.scalar(statement)

    if expense is None or not is_expense_visible(expense, current_user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )
    return expense


def validate_personal_expense_owner(
    db: Session,
    expense_type: DBExpenseType,
    paid_by_id: UUID,
    current_user: User,
) -> None:
    if expense_type != DBExpenseType.PERSONAL:
        return

    payer = db.get(TripMember, paid_by_id)
    if payer is None or payer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Personal expenses can only be recorded for yourself",
        )


def get_participant_ids(
    db: Session,
    trip_id: UUID,
) -> set[UUID]:
    statement = select(TripMember.id).where(
        TripMember.trip_id == trip_id
    )
    return set(db.scalars(statement).all())


def validate_expense_people(
    participant_ids: set[UUID],
    paid_by: UUID,
    split_among: list[UUID],
) -> None:
    if paid_by not in participant_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="paid_by must be an existing participant",
        )

    if len(split_among) != len(set(split_among)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="split_among contains duplicate participants",
        )

    unknown_splitters = sorted(
        set(split_among) - participant_ids,
        key=str,
    )
    if unknown_splitters:
        unknown_ids = [str(item) for item in unknown_splitters]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "split_among contains unknown participants: "
                f"{unknown_ids}"
            ),
        )


def replace_expense_shares(
    db: Session,
    expense: Expense,
    participant_ids: list[UUID],
) -> None:
    expense.shares.clear()
    db.flush()

    shares = split_cents_evenly(
        expense.amount_cents,
        participant_ids,
    )
    expense.shares = [
        ExpenseShare(
            member_id=participant_id,
            amount_cents=share_cents,
        )
        for participant_id, share_cents in shares.items()
    ]


@router.get("", response_model=ExpensePage)
def list_expenses(
    trip_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpensePage:
    find_trip_or_404(db, trip_id, current_user)

    # Same rule as is_expense_visible(), expressed as SQL so pagination
    # and the total count are computed after visibility is applied
    # (not before) — a page can't come up short because it silently
    # includes personal expenses that belong to someone else.
    visible_to_current_user = or_(
        Expense.expense_type == DBExpenseType.SHARED,
        and_(
            Expense.expense_type == DBExpenseType.PERSONAL,
            TripMember.user_id == current_user.id,
        ),
    )

    base_statement = (
        select(Expense)
        .join(Expense.paid_by)
        .where(Expense.trip_id == trip_id, visible_to_current_user)
    )

    total = db.scalar(
        select(func.count()).select_from(base_statement.subquery())
    )

    page_statement = (
        base_statement.options(
            selectinload(Expense.shares),
            selectinload(Expense.paid_by),
        )
        .order_by(
            Expense.expense_date.desc(),
            Expense.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    expenses = db.scalars(page_statement).all()

    return ExpensePage(
        items=[ExpenseRead.model_validate(expense) for expense in expenses],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    trip_id: UUID,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Expense:
    trip = find_trip_or_404(db, trip_id, current_user)
    participant_ids = get_participant_ids(db, trip_id)

    expense_type = DBExpenseType(payload.expense_type.value)
    split_among = (
        [payload.paid_by]
        if expense_type == DBExpenseType.PERSONAL
        else payload.split_among
    )
    validate_expense_people(
        participant_ids,
        payload.paid_by,
        split_among,
    )
    validate_personal_expense_owner(
        db,
        expense_type,
        payload.paid_by,
        current_user,
    )

    expense = Expense(
        trip_id=trip.id,
        paid_by_id=payload.paid_by,
        title=payload.title,
        amount_cents=amount_to_cents(payload.amount),
        expense_type=expense_type,
        category=DBExpenseCategory(payload.category.value),
        expense_date=payload.date,
        currency=(payload.currency or "USD").upper(),
        note=payload.note,
    )

    shares = split_cents_evenly(
        expense.amount_cents,
        split_among,
    )
    expense.shares = [
        ExpenseShare(
            member_id=participant_id,
            amount_cents=share_cents,
        )
        for participant_id, share_cents in shares.items()
    ]

    trip.updated_at = datetime.now(UTC)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    trip_id: UUID,
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Expense:
    find_trip_or_404(db, trip_id, current_user)
    return find_expense_or_404(
        db,
        trip_id,
        expense_id,
        current_user.id,
    )


@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    trip_id: UUID,
    expense_id: UUID,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Expense:
    trip = find_trip_or_404(db, trip_id, current_user)
    expense = find_expense_or_404(
        db,
        trip_id,
        expense_id,
        current_user.id,
    )
    updates = payload.model_dump(exclude_unset=True)

    paid_by = updates.get(
        "paid_by",
        expense.paid_by_id,
    )
    expense_type = (
        DBExpenseType(updates["expense_type"].value)
        if "expense_type" in updates
        and updates["expense_type"] is not None
        else expense.expense_type
    )
    split_among = (
        [paid_by]
        if expense_type == DBExpenseType.PERSONAL
        else updates.get(
            "split_among",
            expense.split_among,
        )
    )

    validate_expense_people(
        get_participant_ids(db, trip_id),
        paid_by,
        split_among,
    )
    validate_personal_expense_owner(
        db,
        expense_type,
        paid_by,
        current_user,
    )

    expense.paid_by_id = paid_by
    expense.expense_type = expense_type

    if updates.get("title") is not None:
        expense.title = updates["title"]
    if updates.get("amount") is not None:
        expense.amount_cents = amount_to_cents(
            updates["amount"]
        )
    if updates.get("category") is not None:
        expense.category = DBExpenseCategory(
            updates["category"].value
        )
    if updates.get("date") is not None:
        expense.expense_date = updates["date"]
    if "currency" in updates:
        expense.currency = (
            updates["currency"] or "USD"
        ).upper()
    if "note" in updates:
        expense.note = updates["note"]

    share_fields = {
        "amount",
        "paid_by",
        "split_among",
        "expense_type",
    }
    if share_fields.intersection(updates):
        replace_expense_shares(
            db,
            expense,
            split_among,
        )

    trip.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_expense(
    trip_id: UUID,
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    trip = find_trip_or_404(db, trip_id, current_user)
    expense = find_expense_or_404(
        db,
        trip_id,
        expense_id,
        current_user.id,
    )

    trip.updated_at = datetime.now(UTC)
    db.delete(expense)
    db.commit()
