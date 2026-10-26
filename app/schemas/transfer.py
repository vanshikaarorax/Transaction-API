import uuid
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.transaction import TransactionOut


class TransferCreate(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reference_id: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=1000)

    @field_validator("reference_id", "description")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def distinct_accounts(self) -> "TransferCreate":
        if self.source_account_id == self.destination_account_id:
            raise ValueError("source and destination accounts must differ")
        return self


class TransferOut(BaseModel):
    reference_id: str
    source_transaction: TransactionOut
    destination_transaction: TransactionOut
