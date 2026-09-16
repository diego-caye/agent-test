from uuid import UUID

from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.models import FeedbackRow


class SqlFeedbackRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def add(
        self, *, session_id: str, user_id: UUID, trace_id: str, score: int, comment: str | None
    ) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(
                FeedbackRow(
                    session_id=session_id,
                    user_id=user_id,
                    trace_id=trace_id,
                    score=score,
                    comment=comment,
                )
            )
