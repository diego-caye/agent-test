from fastapi import APIRouter, Request

from asesor.api.dtos import ModelOption
from asesor.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("", response_model=list[ModelOption])
async def list_models(request: Request) -> list[ModelOption]:
    """Catálogo del selector de modelos.

    Para Ollama, este catálogo no viene de configuración: se descubrió en el
    arranque contra /api/tags + /api/show (ver infrastructure.container),
    así que siempre refleja lo que de verdad hay instalado, con sus
    capacidades reales (supports_tools, supports_thinking).

    `available` es false para las opciones cuyo proveedor no está configurado
    (Gemini sin API key, por ejemplo): la interfaz las muestra deshabilitadas en
    vez de ocultarlas, para que se vea qué hay y por qué no se puede usar.
    """
    container: Container = request.app.state.container
    settings = container.settings
    runners = container.runners

    return [
        ModelOption(
            id=option.id,
            label=option.label,
            provider=option.provider.value,
            model=option.model,
            available=settings.is_usable(option),
            is_default=option.id == runners.default_id,
            supports_tools=option.supports_tools,
            supports_thinking=option.supports_thinking,
        )
        for option in runners.catalog
    ]
