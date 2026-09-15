from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__("NOT_FOUND", message, http_status=status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Missing or invalid credentials") -> None:
        super().__init__("UNAUTHORIZED", message, http_status=status.HTTP_401_UNAUTHORIZED)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFLICT", message, http_status=status.HTTP_409_CONFLICT)


class UpstreamUnavailableError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            "UPSTREAM_UNAVAILABLE",
            message,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
        )


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    body = ErrorBody(code=exc.code, message=exc.message, retryable=exc.retryable)
    return JSONResponse(status_code=exc.http_status, content=body.model_dump())


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    response = await request_validation_exception_handler(request, exc)
    body = ErrorBody(
        code="VALIDATION_ERROR",
        message="Request body or parameters are invalid",
        retryable=False,
    )
    return JSONResponse(status_code=response.status_code, content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
