import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.exceptions import APIError
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionType
from app.services.accounts import get_account_or_404


def create_transaction(db: Session, account_id: uuid.UUID, payload: TransactionCreate) -> Transaction:
    try:
        with db.begin():
            account = get_account_or_404(db, account_id, lock=True)
            # Lock serializes balance changes. The database unique constraint handles races too.
            if db.scalar(select(Transaction.id).where(Transaction.account_id == account_id, Transaction.reference_id == payload.reference_id)):
                raise APIError(409, "DUPLICATE_REFERENCE", "A transaction with this reference already exists for this account.")
            amount = payload.amount
            if payload.type == TransactionType.debit and account.balance < amount:
                raise APIError(409, "INSUFFICIENT_BALANCE", "The account has insufficient funds.")
            transaction = Transaction(account_id=account.id, type=payload.type.value, amount=amount,
                                      description=payload.description, reference_id=payload.reference_id)
            account.balance = account.balance + amount if payload.type == TransactionType.credit else account.balance - amount
            db.add(transaction)
            db.flush()
        db.refresh(transaction)
        return transaction
    except APIError:
        raise
    except IntegrityError as exc:
        # The unique index is authoritative under concurrent duplicate submissions.
        raise APIError(409, "DUPLICATE_REFERENCE", "A transaction with this reference already exists for this account.") from exc
