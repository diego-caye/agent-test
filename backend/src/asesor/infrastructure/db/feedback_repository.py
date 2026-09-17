from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select

from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.models import FeedbackRow


@dataclass(frozen=True, slots=True)
class FeedbackEntry:
    id: int
    session_id: str
    user_id: UUID
    trace_id: str
    score: int
    message: str
    comment: str | None
    created_at: datetime


def _to_entry(row: FeedbackRow) -> FeedbackEntry:
    return FeedbackEntry(
        id=row.id,
        session_id=row.session_id,
        user_id=row.user_id,
        trace_id=row.trace_id,
        score=row.score,
        message=row.message,
        comment=row.comment,
        created_at=row.created_at,
    )


class SqlFeedbackRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def add(
        self,
        *,
        session_id: str,
        user_id: UUID,
        trace_id: str,
        score: int,
        message: str,
        comment: str | None,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(
                FeedbackRow(
                    session_id=session_id,
                    user_id=user_id,
                    trace_id=trace_id,
                    score=score,
                    message=message,
                    comment=comment,
                )
            )

    async def list(self, limit: int = 100) -> list[FeedbackEntry]:
        statement = select(FeedbackRow).order_by(FeedbackRow.created_at.desc()).limit(limit)
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
            return [_to_entry(row) for row in rows]

    async def delete_for_session(self, session_id: str) -> None:
        # Igual que session_titles: el feedback vive aparte de la sesión de
        # ADK, así que borrarla no lo arrastra solo -- si no se limpia a
        # mano, el panel de feedback queda con filas que apuntan a una
        # sesión que ya no existe (el clic para "ir a la conversación" no
        # tendría a dónde ir).
        async with self._session_factory() as session, session.begin():
            await session.execute(delete(FeedbackRow).where(FeedbackRow.session_id == session_id))
