from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from asesor.domain.knowledge import EMBEDDING_DIMENSIONS


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


class HandoffRow(Base):
    __tablename__ = "handoffs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), index=True)
    motivo: Mapped[str] = mapped_column(String(24))
    resumen_requerimiento: Mapped[str] = mapped_column(Text)
    canal_preferido: Mapped[str | None] = mapped_column(String(16), default=None)
    urgencia: Mapped[str | None] = mapped_column(String(8), default=None)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # Idempotencia de spec 03: como maximo un handoff OPEN por sesion.
        Index(
            "ux_handoffs_one_open_per_session",
            "session_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )


class KbChunkRow(Base):
    __tablename__ = "kb_chunks"

    chunk_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    categoria: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(64), index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_kb_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
