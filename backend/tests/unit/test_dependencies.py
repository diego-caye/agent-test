from uuid import uuid4

import pytest

from asesor.api.dependencies import get_user_id
from asesor.api.errors import UnauthorizedError


def test_accepts_valid_uuid() -> None:
    user_id = uuid4()
    assert get_user_id(str(user_id)) == user_id


def test_rejects_missing_header() -> None:
    with pytest.raises(UnauthorizedError, match="Missing X-User-Id"):
        get_user_id(None)


def test_rejects_non_uuid_header() -> None:
    with pytest.raises(UnauthorizedError, match="must be a UUID"):
        get_user_id("not-a-uuid")
