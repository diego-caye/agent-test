import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OllamaModelInfo:
    """Un modelo de chat instalado en Ollama, con sus capacidades reales."""

    name: str  # tal cual lo devuelve Ollama, p. ej. "gemma4:12b"
    supports_tools: bool
    supports_thinking: bool


async def discover_ollama_models(api_base: str, timeout: float = 10.0) -> list[OllamaModelInfo]:
    """Modelos de chat instalados en Ollama ahora mismo, vía /api/tags + /api/show.

    Nada de esto se declara a mano: el catálogo del selector para Ollama sale
    de lo que el servidor reporta tener *pulled*, así nunca queda
    desincronizado de la realidad (un modelo borrado, uno nuevo, un tag
    distinto al de la última vez que alguien tocó el .env).

    /api/show trae `capabilities`, una lista como ["completion", "tools",
    "thinking"] o ["embedding"]. Se descartan los modelos sin "completion"
    (los de solo-embeddings, como embeddinggemma, no sirven para el chat y
    solo ensuciarían el selector).

    Si Ollama no responde (apagado, arrancando, URL mal puesta), se devuelve
    una lista vacía en vez de tumbar el arranque del backend: el selector
    queda sin opciones locales, no es un fallo fatal.
    """
    async with httpx.AsyncClient(base_url=api_base, timeout=timeout) as client:
        try:
            tags_response = await client.get("/api/tags")
            tags_response.raise_for_status()
        except httpx.HTTPError:
            logger.warning("no se pudo listar los modelos de Ollama en %s", api_base, exc_info=True)
            return []

        names = [entry["name"] for entry in tags_response.json().get("models", [])]

        models: list[OllamaModelInfo] = []
        for name in names:
            try:
                show_response = await client.post("/api/show", json={"model": name})
                show_response.raise_for_status()
            except httpx.HTTPError:
                logger.warning("no se pudo consultar /api/show para %s", name, exc_info=True)
                continue

            capabilities = set(show_response.json().get("capabilities") or [])
            if "completion" not in capabilities:
                continue

            models.append(
                OllamaModelInfo(
                    name=name,
                    supports_tools="tools" in capabilities,
                    supports_thinking="thinking" in capabilities,
                )
            )

        return models
