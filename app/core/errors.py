import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def format_validation_errors(errors: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for err in errors:
        loc = err.get("loc", ())
        field = loc[-1] if loc else "request"
        msg = err.get("msg", "Invalid value")
        parts.append(f"{field}: {msg}")
    return " · ".join(parts)


def json_error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "ok": False})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        detail = format_validation_errors(exc.errors())
        logger.warning("Validation error: %s", detail)
        return json_error(422, detail)

    @app.exception_handler(ResponseValidationError)
    async def response_validation_error_handler(_: Request, exc: ResponseValidationError):
        detail = f"Response validation failed: {exc.errors()}"
        logger.exception("Response validation error")
        return json_error(500, detail)

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return json_error(exc.status_code, detail)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(_: Request, exc: SQLAlchemyError):
        detail = str(getattr(exc, "orig", exc))
        logger.exception("Database error")
        return json_error(400, f"Database error: {detail}")

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        logger.exception("Unhandled error")
        return json_error(500, str(exc) or exc.__class__.__name__)
