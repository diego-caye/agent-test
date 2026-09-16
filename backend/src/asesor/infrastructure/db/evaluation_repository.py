from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.models import EvaluationRow


class SqlEvaluationRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def add(
        self, *, session_id: str, message_id: str, criterio: str, score: float, justificacion: str
    ) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(
                EvaluationRow(
                    session_id=session_id,
                    message_id=message_id,
                    criterio=criterio,
                    score=score,
                    justificacion=justificacion,
                )
            )
