from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LeadRow(Base):
    __tablename__ = "leads"

    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    nombre: Mapped[str | None] = mapped_column(String(80), default=None)
    telefono: Mapped[str | None] = mapped_column(String(20), default=None)
    email: Mapped[str | None] = mapped_column(String(254), default=None)
    canal_preferido: Mapped[str | None] = mapped_column(String(16), default=None)
    consentimiento_contacto: Mapped[bool] = mapped_column(Boolean, default=False)
    uso_principal: Mapped[str | None] = mapped_column(String(16), default=None)
    tipo_vehiculo_interes: Mapped[str | None] = mapped_column(String(16), default=None)
    motorizacion_interes: Mapped[str | None] = mapped_column(String(16), default=None)
    nivel_interes: Mapped[str | None] = mapped_column(String(8), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
