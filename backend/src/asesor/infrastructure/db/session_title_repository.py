from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.models import SessionTitleRow


class SqlSessionTitleRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def get(self, session_id: str) -> str | None:
        async with self._session_factory() as session:
            title = await session.scalar(
                select(SessionTitleRow.title).where(SessionTitleRow.session_id == session_id)
            )
            return str(title) if title is not None else None

    async def get_many(self, session_ids: list[str]) -> dict[str, str]:
        """Un solo round-trip para toda la lista de sesiones, no uno por fila."""
        if not session_ids:
            return {}

        async with self._session_factory() as session:
            rows = await session.execute(
                select(SessionTitleRow.session_id, SessionTitleRow.title).where(
                    SessionTitleRow.session_id.in_(session_ids)
                )
            )
            return {session_id: title for session_id, title in rows.all()}

    async def upsert(self, session_id: str, user_id: UUID, title: str) -> None:
        async with self._session_factory() as session, session.begin():
            statement = (
                pg_insert(SessionTitleRow)
                .values(session_id=session_id, user_id=user_id, title=title)
                .on_conflict_do_update(
                    index_elements=[SessionTitleRow.session_id],
                    set_={"title": title},
                )
            )
            await session.execute(statement)

    async def delete(self, session_id: str) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                delete(SessionTitleRow).where(SessionTitleRow.session_id == session_id)
            )
