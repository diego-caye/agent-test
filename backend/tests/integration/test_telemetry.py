import json

import httpx
import pytest

from asesor.config import Settings
from asesor.infrastructure.telemetry import send_langfuse_score, setup_telemetry, turn_span


def test_turn_span_yields_a_trace_id_without_langfuse_keys(settings: Settings) -> None:
    assert settings.telemetry_enabled is False
    setup_telemetry(settings)

    with turn_span(session_id="s1", user_id="u1", settings=settings) as turn:
        assert len(turn.trace_id) == 32
        assert int(turn.trace_id, 16) != 0


def _patch_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    class _PatchedClient(httpx.AsyncClient):
        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("asesor.infrastructure.telemetry.httpx.AsyncClient", _PatchedClient)


async def test_send_langfuse_score_es_no_op_sin_keys(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert settings.telemetry_enabled is False

    def handle(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no deberia llamar a Langfuse sin keys configuradas")

    _patch_client(monkeypatch, httpx.MockTransport(handle))

    await send_langfuse_score(settings, trace_id="t1", name="user-feedback", value=1)


async def test_send_langfuse_score_manda_basic_auth_y_payload_correcto(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.langfuse_public_key = "pk-test"
    settings.langfuse_secret_key = "sk-test"
    settings.langfuse_host = "https://lf.test"
    seen: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "score-1"})

    _patch_client(monkeypatch, httpx.MockTransport(handle))

    await send_langfuse_score(
        settings, trace_id="t1", name="user-feedback", value=-1, comment="mala experiencia"
    )

    assert seen["url"] == "https://lf.test/api/public/scores"
    assert isinstance(seen["auth"], str) and seen["auth"].startswith("Basic ")
    assert seen["body"] == {
        "traceId": "t1",
        "name": "user-feedback",
        "value": -1,
        "dataType": "NUMERIC",
        "comment": "mala experiencia",
    }


async def test_send_langfuse_score_nunca_lanza_si_langfuse_falla(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.langfuse_public_key = "pk-test"
    settings.langfuse_secret_key = "sk-test"

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    _patch_client(monkeypatch, httpx.MockTransport(handle))

    await send_langfuse_score(settings, trace_id="t1", name="user-feedback", value=1)
