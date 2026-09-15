from collections.abc import AsyncIterator
from uuid import UUID

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, Session
from google.genai import types

from asesor.agent.factory import APP_NAME


class SessionNotFoundError(LookupError):
    pass


class ChatService:
    def __init__(self, runner: Runner, session_service: BaseSessionService) -> None:
        self._runner = runner
        self._session_service = session_service

    async def create_session(self, user_id: UUID) -> str:
        session = await self._session_service.create_session(
            app_name=APP_NAME, user_id=str(user_id)
        )
        return session.id

    async def list_sessions(self, user_id: UUID) -> list[Session]:
        response = await self._session_service.list_sessions(
            app_name=APP_NAME, user_id=str(user_id)
        )
        return list(response.sessions)

    async def get_session(self, user_id: UUID, session_id: str) -> Session:
        session = await self._session_service.get_session(
            app_name=APP_NAME, user_id=str(user_id), session_id=session_id
        )
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    async def run_turn(self, user_id: UUID, session_id: str, message: str) -> AsyncIterator[Event]:
        await self.get_session(user_id, session_id)

        content = types.Content(role="user", parts=[types.Part.from_text(text=message)])
        async for event in self._runner.run_async(
            user_id=str(user_id),
            session_id=session_id,
            new_message=content,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            yield event
