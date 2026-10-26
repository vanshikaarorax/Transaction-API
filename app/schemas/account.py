import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    balance: Decimal
    created_at: datetime


class BalanceOut(BaseModel):
    account_id: uuid.UUID
    balance: Decimal
