from typing import Any

from asesor.domain.enums import ToolStatus


def ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"status": ToolStatus.OK.value, "data": data}


def no_results() -> dict[str, Any]:
    return {"status": ToolStatus.NO_RESULTS.value, "data": None}


def error(code: str, message: str, *, retryable: bool = False) -> dict[str, Any]:
    return {
        "status": ToolStatus.ERROR.value,
        "error": {"code": code, "message": message, "retryable": retryable},
    }
