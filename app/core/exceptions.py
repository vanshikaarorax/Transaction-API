from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code, self.message = status_code, code, message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


async def integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    return error_response(409, "INTEGRITY_CONFLICT", "The request conflicts with existing ledger data.")
