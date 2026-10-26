import uuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.exceptions import APIError
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transfer import TransferCreate


def _locked_accounts(db: Session, source_id: uuid.UUID, destination_id: uuid.UUID) -> dict[uuid.UUID, Account]:
    """Load both accounts under locks in UUID order to minimize PostgreSQL deadlocks."""
    accounts: dict[uuid.UUID, Account] = {}
    for account_id in sorted((source_id, destination_id), key=str):
        statement = select(Account).where(Account.id == account_id)
        if db.bind and db.bind.dialect.name == "postgresql":
            statement = statement.with_for_update()
        account = db.scalar(statement)
        if account is None:
            raise APIError(404, "ACCOUNT_NOT_FOUND", "A transfer account does not exist.")
        accounts[account_id] = account
    return accounts


def create_transfer(db: Session, payload: TransferCreate) -> tuple[Transaction, Transaction]:
    try:
        with db.begin():
            accounts = _locked_accounts(db, payload.source_account_id, payload.destination_account_id)
            source = accounts[payload.source_account_id]
            destination = accounts[payload.destination_account_id]
            # A transfer reference is scoped to the source account. The normal ledger
            # uniqueness constraint also protects each corresponding account entry.
            if db.scalar(select(Transaction.id).where(
                Transaction.account_id == source.id, Transaction.reference_id == payload.reference_id
            )):
                raise APIError(409, "DUPLICATE_TRANSFER_REFERENCE", "This transfer reference already exists for the source account.")
            if source.balance < payload.amount:
                raise APIError(409, "INSUFFICIENT_BALANCE", "The source account has insufficient funds.")
            source_transaction = Transaction(account_id=source.id, type="debit", amount=payload.amount,
                                             description=payload.description, reference_id=payload.reference_id)
            destination_transaction = Transaction(account_id=destination.id, type="credit", amount=payload.amount,
                                                  description=payload.description, reference_id=payload.reference_id)
            source.balance -= payload.amount
            destination.balance += payload.amount
            db.add_all([source_transaction, destination_transaction])
            db.flush()
        db.refresh(source_transaction)
        db.refresh(destination_transaction)
        return source_transaction, destination_transaction
    except APIError:
        raise
    except IntegrityError as exc:
        raise APIError(409, "DUPLICATE_TRANSFER_REFERENCE", "This transfer conflicts with an existing transaction reference.") from exc
