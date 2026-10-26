import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.exceptions import APIError
from app.models.account import Account


def get_account_or_404(db: Session, account_id: uuid.UUID, *, lock: bool = False) -> Account:
    statement = select(Account).where(Account.id == account_id)
    # PostgreSQL locks the account row; SQLite tests use its transactional semantics.
    if lock and db.bind and db.bind.dialect.name == "postgresql":
        statement = statement.with_for_update()
    account = db.scalar(statement)
    if account is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "The account does not exist.")
    return account
