from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.routes.accounts import router as accounts_router
from app.api.routes.transfers import router as transfers_router
from app.core.exceptions import APIError, api_error_handler, error_response, integrity_error_handler
from sqlalchemy.exc import IntegrityError

app = FastAPI(title="Transaction Ledger API", version="1.0.0")
app.include_router(accounts_router)
app.include_router(transfers_router)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "Invalid request data.")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
