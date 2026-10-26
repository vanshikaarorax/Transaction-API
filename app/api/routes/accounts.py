import math
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.account import AccountCreate, AccountOut, BalanceOut
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionPage, TransactionType
from app.services.accounts import get_account_or_404
from app.services.transactions import create_transaction

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)) -> Account:
    account = Account(name=payload.name)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}/balance", response_model=BalanceOut)
def get_balance(account_id: uuid.UUID, db: Session = Depends(get_db)) -> BalanceOut:
    account = get_account_or_404(db, account_id)
    return BalanceOut(account_id=account.id, balance=account.balance)


@router.post("/{account_id}/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def add_transaction(account_id: uuid.UUID, payload: TransactionCreate, db: Session = Depends(get_db)) -> Transaction:
    return create_transaction(db, account_id, payload)


@router.get("/{account_id}/transactions", response_model=TransactionPage)
def transaction_history(
    account_id: uuid.UUID,
    type: TransactionType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TransactionPage:
    get_account_or_404(db, account_id)
    filters = [Transaction.account_id == account_id]
    if type is not None:
        filters.append(Transaction.type == type.value)
    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
    items = db.scalars(select(Transaction).where(*filters).order_by(Transaction.created_at.desc(), Transaction.id.desc())
                       .offset((page - 1) * limit).limit(limit)).all()
    return TransactionPage(items=items, current_page=page, page_size=limit, total_records=total,
                           total_pages=math.ceil(total / limit) if total else 0)
