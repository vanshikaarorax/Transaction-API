from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.transfer import TransferCreate, TransferOut
from app.services.transfers import create_transfer

router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"])


@router.post("", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def transfer(payload: TransferCreate, db: Session = Depends(get_db)) -> TransferOut:
    source_transaction, destination_transaction = create_transfer(db, payload)
    return TransferOut(reference_id=payload.reference_id, source_transaction=source_transaction,
                       destination_transaction=destination_transaction)
