import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionType(str, Enum):
    credit = "credit"
    debit = "debit"


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str = Field(min_length=1, max_length=1000)
    reference_id: str = Field(min_length=1, max_length=255)

    @field_validator("description", "reference_id")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value.strip()


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_id: uuid.UUID
    type: TransactionType
    amount: Decimal
    description: str
    reference_id: str
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    current_page: int
    page_size: int
    total_records: int
    total_pages: int
