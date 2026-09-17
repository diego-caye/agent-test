from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request

from asesor.api.errors import UnauthorizedError
from asesor.infrastructure.container import Container


def get_user_id(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    if not x_user_id:
        raise UnauthorizedError("Missing X-User-Id header")
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise UnauthorizedError("X-User-Id must be a UUID") from exc


UserId = Annotated[UUID, Depends(get_user_id)]


def require_admin(request: Request, authorization: Annotated[str | None, Header()] = None) -> None:
    # /handoffs y /feedback (listado) cruzan sesiones ajenas: van con
    # admin_token por Bearer, no con el UserId normal de un usuario.
    container: Container = request.app.state.container
    expected = f"Bearer {container.settings.admin_token}"
    if not authorization or authorization != expected:
        raise UnauthorizedError("Admin token required")


Admin = Annotated[None, Depends(require_admin)]
