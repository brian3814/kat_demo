"""Google ADK Agent setup with Runner and session management.

This module sets up the ADK Agent with USD tools and manages
the Runner for handling conversations with session context.

"""

import asyncio
from textwrap import dedent
from typing import Optional, AsyncGenerator, Dict, Any

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.genai import types

from ..config import Settings
from ..utils.logger import get_logger
from .session_manager import get_session_manager, SessionManager
from ..tools.usd_tools import USD_TOOLS

logger = get_logger()


# System instruction for the Omniverse assistant
SYSTEM_INSTRUCTION = dedent("""\
    You are an intelligent assistant for NVIDIA Omniverse, helping users work with 3D scenes and USD (Universal Scene Description) content.

    Your capabilities include:
    - Analyzing what the user is looking at in the viewport using raycast
    - Getting information about selected prims (3D objects)
    - Retrieving detailed properties of specific prims
    - Creating new 3D primitives (cubes, spheres, cylinders, cones)
    - Listing all prims in the scene hierarchy
    - Understanding camera position and orientation

    Guidelines:
    1. When the user asks "what am I looking at" or similar, use the raycast_from_camera tool
    2. When the user asks about their selection, use the get_selection tool
    3. When the user wants to create objects, use the create_prim tool with appropriate parameters
    4. When exploring the scene, use list_all_prims to understand the hierarchy
    5. Always provide clear, helpful responses about the 3D scene
    6. If a tool returns an error, explain it clearly to the user

    Be conversational but concise. Focus on helping users understand and manipulate their 3D scenes effectively.
""")


class OmniverseAgent:
    """
    Wrapper class for the Omniverse ADK Agent.

    Manages agent lifecycle and provides interface for running conversations
    with session context.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the Omniverse agent.

        Args:
            settings: Application settings with model configuration
        """
        self.settings = settings
        self.agent: Optional[Agent] = None
        self.runner: Optional[Runner] = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """
        Initialize the ADK Agent and Runner.

        Creates the agent with USD tools and sets up the Runner
        with session service for context management.
        """
        async with self._lock:
            if self._initialized:
                logger.info("OmniverseAgent already initialized")
                return

            try:
                logger.info(
                    "Initializing OmniverseAgent",
                    model=self.settings.model_name
                )

                # Create the agent with USD tools
                self.agent = Agent(
                    name="omniverse_assistant",
                    model=self.settings.model_name,
                    description="An intelligent assistant for NVIDIA Omniverse that helps users work with 3D scenes and USD content.",
                    instruction=SYSTEM_INSTRUCTION,
                    tools=USD_TOOLS,
                )

                # Create the runner with session service
                session_manager = get_session_manager()
                self.runner = Runner(
                    agent=self.agent,
                    app_name=session_manager.APP_NAME,
                    session_service=session_manager.session_service,
                )

                self._initialized = True
                logger.info("OmniverseAgent initialized successfully")

            except Exception as e:
                logger.error("Failed to initialize OmniverseAgent", error=str(e))
                raise

    async def run_conversation(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run a conversation turn with the agent.

        Args:
            message: User message
            user_id: User identifier
            session_id: Optional session ID for continuing a conversation

        Yields:
            Dict with event type and data
        """
        if not self._initialized or self.runner is None:
            raise RuntimeError("OmniverseAgent not initialized")

        try:
            # Get or create session
            session_manager = get_session_manager()
            session = await session_manager.get_or_create_session(user_id, session_id)
            current_session_id = session.id

            logger.info(
                "Running conversation",
                user_id=user_id,
                session_id=current_session_id,
                message_length=len(message)
            )

            # Create content for the message
            content = types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )

            # Run the agent and stream events
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=current_session_id,
                new_message=content
            ):
                # Convert ADK events to our format
                event_data = self._convert_event(event)
                if event_data:
                    yield event_data

            # Yield completion event
            yield {
                "type": "end",
                "session_id": current_session_id,
                "done": True
            }

            logger.info(
                "Conversation completed",
                user_id=user_id,
                session_id=current_session_id
            )

        except Exception as e:
            logger.error(
                "Error during conversation",
                error=str(e),
                user_id=user_id
            )
            yield {
                "type": "error",
                "error": str(e),
                "done": True
            }

    def _convert_event(self, event) -> Optional[Dict[str, Any]]:
        """
        Convert ADK event to our response format.

        Args:
            event: ADK event object

        Returns:
            Dict with event data or None if event should be skipped
        """
        try:
            # Handle different event types based on ADK event structure
            # The exact structure depends on the ADK version

            # Check for text content
            if hasattr(event, 'content') and event.content:
                content = event.content
                if hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            return {
                                "type": "text_delta",
                                "content": part.text,
                                "done": False
                            }
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            return {
                                "type": "tool_call",
                                "tool": fc.name,
                                "params": dict(fc.args) if fc.args else {},
                                "done": False
                            }
                        if hasattr(part, 'function_response') and part.function_response:
                            fr = part.function_response
                            return {
                                "type": "tool_result",
                                "tool": fr.name,
                                "result": fr.response,
                                "done": False
                            }

            # Check for actions (tool calls in newer ADK)
            if hasattr(event, 'actions'):
                for action in event.actions:
                    if hasattr(action, 'tool_name'):
                        return {
                            "type": "tool_call",
                            "tool": action.tool_name,
                            "params": action.tool_input if hasattr(action, 'tool_input') else {},
                            "done": False
                        }

            return None

        except Exception as e:
            logger.warning(f"Error converting event: {e}")
            return None

    async def shutdown(self) -> None:
        """Clean up agent resources."""
        async with self._lock:
            if self._initialized:
                logger.info("Shutting down OmniverseAgent")
                self.agent = None
                self.runner = None
                self._initialized = False
                logger.info("OmniverseAgent shut down")

    @property
    def is_ready(self) -> bool:
        """Check if agent is initialized and ready."""
        return self._initialized and self.runner is not None


# Global agent instance
_omniverse_agent: Optional[OmniverseAgent] = None


def get_omniverse_agent() -> OmniverseAgent:
    """
    Get the global OmniverseAgent instance.

    Returns:
        OmniverseAgent: Global agent instance

    Raises:
        RuntimeError: If agent not initialized
    """
    if _omniverse_agent is None:
        raise RuntimeError("OmniverseAgent not initialized")
    return _omniverse_agent


def set_omniverse_agent(agent: OmniverseAgent) -> None:
    """Set the global OmniverseAgent instance."""
    global _omniverse_agent
    _omniverse_agent = agent


async def create_omniverse_agent(settings: Settings) -> OmniverseAgent:
    """
    Create and initialize the OmniverseAgent.

    Args:
        settings: Application settings

    Returns:
        OmniverseAgent: Initialized agent
    """
    agent = OmniverseAgent(settings)
    await agent.initialize()
    set_omniverse_agent(agent)
    return agent
