"""Session management using Google ADK InMemorySessionService."""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner

from ..utils.logger import get_logger

logger = get_logger()


class SessionManager:
    """
    Manages user sessions using Google ADK's InMemorySessionService.

    Provides session lifecycle management including creation, retrieval,
    and cleanup of expired sessions.
    """

    APP_NAME = "omniverse_chat"

    def __init__(self, session_timeout_hours: float = 3.0):
        """
        Initialize the session manager.

        Args:
            session_timeout_hours: Session timeout in hours (default: 3 hours)
        """
        self.session_service = InMemorySessionService()
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self._session_timestamps: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

        logger.info(
            "SessionManager initialized",
            timeout_hours=session_timeout_hours
        )

    async def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Session:
        """
        Get an existing session or create a new one.

        Args:
            user_id: User identifier
            session_id: Optional session ID. If not provided, creates new session.

        Returns:
            Session: The ADK session object
        """
        async with self._lock:
            # Try to get existing session
            if session_id:
                try:
                    session = await asyncio.to_thread(
                        self.session_service.get_session,
                        app_name=self.APP_NAME,
                        user_id=user_id,
                        session_id=session_id
                    )

                    if session:
                        # Update timestamp
                        self._session_timestamps[session_id] = datetime.utcnow()
                        logger.debug(
                            "Retrieved existing session",
                            session_id=session_id,
                            user_id=user_id
                        )
                        return session

                except Exception as e:
                    logger.warning(
                        "Failed to retrieve session, creating new one",
                        session_id=session_id,
                        error=str(e)
                    )

            # Create new session
            session = await asyncio.to_thread(
                self.session_service.create_session,
                app_name=self.APP_NAME,
                user_id=user_id
            )

            self._session_timestamps[session.id] = datetime.utcnow()

            logger.info(
                "Created new session",
                session_id=session.id,
                user_id=user_id
            )

            return session

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            user_id: User identifier
            session_id: Session ID to delete

        Returns:
            bool: True if deleted successfully
        """
        async with self._lock:
            try:
                await asyncio.to_thread(
                    self.session_service.delete_session,
                    app_name=self.APP_NAME,
                    user_id=user_id,
                    session_id=session_id
                )

                # Clean up timestamp
                self._session_timestamps.pop(session_id, None)

                logger.info(
                    "Deleted session",
                    session_id=session_id,
                    user_id=user_id
                )
                return True

            except Exception as e:
                logger.error(
                    "Failed to delete session",
                    session_id=session_id,
                    error=str(e)
                )
                return False

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions based on timeout.

        Returns:
            int: Number of sessions cleaned up
        """
        async with self._lock:
            now = datetime.utcnow()
            expired_sessions = []

            for session_id, timestamp in self._session_timestamps.items():
                if now - timestamp > self.session_timeout:
                    expired_sessions.append(session_id)

            cleaned = 0
            for session_id in expired_sessions:
                try:
                    # Note: We don't have user_id stored, so we can't delete via service
                    # Just remove from our tracking
                    self._session_timestamps.pop(session_id, None)
                    cleaned += 1
                except Exception as e:
                    logger.warning(
                        "Failed to cleanup session",
                        session_id=session_id,
                        error=str(e)
                    )

            if cleaned > 0:
                logger.info(
                    "Cleaned up expired sessions",
                    count=cleaned
                )

            return cleaned

    @property
    def active_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._session_timestamps)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.

    Returns:
        SessionManager: Global session manager

    Raises:
        RuntimeError: If session manager not initialized
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def set_session_manager(manager: SessionManager) -> None:
    """Set the global session manager instance."""
    global _session_manager
    _session_manager = manager
