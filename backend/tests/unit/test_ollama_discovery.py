import json
from collections.abc import Callable

import httpx
import pytest

from asesor.infrastructure.llm.ollama_discovery import OllamaModelInfo, discover_ollama_models


def _handler(
    tags: dict[str, list[dict[str, str]]], shows: dict[str, dict[str, object]]
) -> "Callable[[httpx.Request], httpx.Response]":
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=tags)
        if request.url.path == "/api/show":
            model = json.loads(request.content)["model"]
            return httpx.Response(200, json=shows[model])
        raise AssertionError(f"ruta inesperada: {request.url.path}")

    return handle


def _patch_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    class _PatchedClient(httpx.AsyncClient):
        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "asesor.infrastructure.llm.ollama_discovery.httpx.AsyncClient", _PatchedClient
    )


async def _discover_with(
    monkeypatch: pytest.MonkeyPatch,
    tags: dict[str, list[dict[str, str]]],
    shows: dict[str, dict[str, object]],
) -> list[OllamaModelInfo]:
    _patch_client(monkeypatch, httpx.MockTransport(_handler(tags, shows)))
    return await discover_ollama_models("http://ollama-fake:11434")


async def test_incluye_modelos_de_chat_con_sus_capacidades(monkeypatch: pytest.MonkeyPatch) -> None:
    tags = {"models": [{"name": "gemma4:latest"}, {"name": "qwen3:4b"}]}
    shows: dict[str, dict[str, object]] = {
        "gemma4:latest": {"capabilities": ["completion", "tools", "thinking"]},
        "qwen3:4b": {"capabilities": ["completion", "tools"]},
    }

    models = await _discover_with(monkeypatch, tags, shows)

    assert models == [
        OllamaModelInfo(name="gemma4:latest", supports_tools=True, supports_thinking=True),
        OllamaModelInfo(name="qwen3:4b", supports_tools=True, supports_thinking=False),
    ]


async def test_descarta_los_modelos_de_solo_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    tags = {"models": [{"name": "gemma4:latest"}, {"name": "embeddinggemma:latest"}]}
    shows: dict[str, dict[str, object]] = {
        "gemma4:latest": {"capabilities": ["completion", "tools", "thinking"]},
        "embeddinggemma:latest": {"capabilities": ["embedding"]},
    }

    models = await _discover_with(monkeypatch, tags, shows)

    assert [m.name for m in models] == ["gemma4:latest"]


async def test_ollama_inalcanzable_devuelve_lista_vacia(monkeypatch: pytest.MonkeyPatch) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _patch_client(monkeypatch, httpx.MockTransport(handle))

    models = await discover_ollama_models("http://ollama-apagado:11434")

    assert models == []
