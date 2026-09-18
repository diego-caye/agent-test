from fastapi.testclient import TestClient

from asesor.config import get_settings
from asesor.main import create_app


def test_healthz_returns_ok() -> None:
    with TestClient(create_app(get_settings())) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_is_served() -> None:
    with TestClient(create_app(get_settings())) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/healthz" in response.json()["paths"]
