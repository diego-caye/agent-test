from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    session_id: str


class SessionSummary(BaseModel):
    session_id: str
    last_update_time: datetime
    etapa: str


class MessageDto(BaseModel):
    role: str
    content: str
    created_at: datetime


class LeadDto(BaseModel):
    nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    canal_preferido: str | None = None
    consentimiento_contacto: bool = False
    uso_principal: str | None = None
    tipo_vehiculo_interes: str | None = None
    motorizacion_interes: str | None = None
    nivel_interes: str | None = None


class LeadResponse(BaseModel):
    lead: LeadDto | None
    etapa: str
    solo_mirando: bool


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=2000)


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    db: str
    llm: str
    detail: dict[str, Any] | None = None
