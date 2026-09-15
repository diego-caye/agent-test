from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from asesor.api.errors import UnauthorizedError


def get_user_id(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    if not x_user_id:
        raise UnauthorizedError("Missing X-User-Id header")
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise UnauthorizedError("X-User-Id must be a UUID") from exc


UserId = Annotated[UUID, Depends(get_user_id)]
