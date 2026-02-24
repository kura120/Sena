# src/api/routes/chat.py
"""Chat API routes for main conversation endpoint."""

import json
import re
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.deps import get_memory_manager, get_sena
from src.api.models.requests import ChatRequest
from src.api.models.responses import ChatMetadata, ChatResponse, ErrorResponse
from src.core.sena import Sena
from src.memory.manager import MemoryManager
from src.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["Chat"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REMEMBER_RE = re.compile(
    r"^remember\s+(?:this|that|these|those|the\s+following|following)?\s*:?\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


def _extract_remember_content(message: str) -> str | None:
    """Return the content the user wants stored, or None if not a store request.

    Handles patterns like:
    - "remember this number: 6"  → "number: 6"
    - "remember that I prefer dark mode"  → "I prefer dark mode"
    - "remember: my API key is abc123"  → "my API key is abc123"
    - "remember my birthday is March 15"  → "my birthday is March 15"
    """
    m = _REMEMBER_RE.match(message.strip())
    if not m:
        return None
    content = m.group(1).strip().lstrip(":").strip()
    return content if content else None


@router.post(
    "",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Send a message to Sena",
    description="Process a user message and get a response from Sena.",
    status_code=200,
)
async def chat(
    request: ChatRequest,
    sena: Sena = Depends(get_sena),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> ChatResponse:
    """Process a chat message and return response."""
    session_id = None
    try:
        logger.info(f"=== CHAT REQUEST START ===")
        logger.info(f"Request payload: {request.model_dump()}")

        if not request.message or not request.message.strip():
            logger.warning(f"Empty message received")
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        session_id = request.session_id or str(uuid.uuid4())[:12]
        timestamp = datetime.now()

        logger.info(f"Processing chat - session={session_id}, message_length={len(request.message)}")
        logger.debug(f"Message preview: {request.message[:100]}...")

        logger.info("Adding message to memory context...")
        try:
            # --- Explicit "remember ..." store detection ---
            remember_content = _extract_remember_content(request.message)
            if remember_content:
                await memory_mgr.remember(
                    content=remember_content,
                    metadata={
                        "session_id": session_id,
                        "source": "explicit_remember",
                        "context": "User explicitly asked Sena to remember this information",
                        "origin": "user_explicit",
                        "original_message": request.message,
                        "timestamp": timestamp.isoformat(),
                    },
                )
                logger.info(
                    f"Stored explicit memory: '{remember_content[:80]}...' "
                    if len(remember_content) > 80
                    else f"Stored explicit memory: '{remember_content}'"
                )

            # Add user message to short-term context
            await memory_mgr.add_to_context(
                content=request.message,
                role="user",
                metadata={"session_id": session_id, "timestamp": timestamp.isoformat()},
            )
            logger.debug("Message added to memory successfully")
        except Exception as mem_err:
            logger.warning(f"Memory context error: {mem_err}, continuing without memory", exc_info=True)

        # Process the message through Sena
        logger.info("Processing message through Sena...")
        logger.info(f"Sena initialized: {sena.is_initialized}")
        response = None
        response_content = ""
        try:
            response = await sena.process(
                user_input=request.message,
                stream=False,
            )
            logger.info(f"Sena processing complete, response type: {type(response)}")
            response_content = getattr(response, "content", None) or getattr(response, "response", "")
            logger.debug(f"Response content length: {len(response_content)}")
        except Exception as process_err:
            logger.error(f"SENA PROCESSING ERROR: {type(process_err).__name__}: {process_err}", exc_info=True)
            # Fallback response
            response_content = f"I encountered an error processing your request: {str(process_err)}. Please ensure Ollama is running and try again."

        logger.info("Storing assistant response in memory...")
        try:
            # Add assistant response to memory
            await memory_mgr.add_to_context(
                content=response_content,
                role="assistant",
                metadata={"session_id": session_id, "timestamp": datetime.now().isoformat()},
            )
            logger.debug("Response stored in memory successfully")
        except Exception as mem_err:
            logger.warning(f"Memory storage error: {mem_err}", exc_info=True)

        logger.info("Extracting learnings from conversation...")
        try:
            # Extract learnings from conversation if enabled
            conversation = await memory_mgr.get_conversation_context()
            await memory_mgr.extract_and_store_learnings(
                conversation=conversation,
                metadata={
                    "session_id": session_id,
                    "context": "Auto-extracted from conversation",
                    "origin": "auto_extraction",
                },
            )
            logger.debug("Learnings extracted successfully")
        except Exception as learn_err:
            logger.warning(f"Learning extraction error: {learn_err}", exc_info=True)

        logger.info(f"Building chat response for session {session_id}")
        if response:
            chat_meta = {
                "session_id": session_id,
                "model": getattr(response, "model", "ollama"),
                "prompt_tokens": int(getattr(response, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(response, "completion_tokens", 0) or 0),
                "total_tokens": int(getattr(response, "total_tokens", 0) or 0),
                "duration_ms": float(getattr(response, "duration_ms", 0) or 0),
                "message_length": len(request.message),
                "response_length": len(response_content),
            }
            logger.info(f"[CHAT] {json.dumps(chat_meta, separators=(',', ':'))}")
        chat_response = ChatResponse(
            response=response_content,
            session_id=session_id,
            metadata=ChatMetadata(
                model_used=getattr(response, "model", "ollama") if response else "ollama",
                processing_time_ms=getattr(response, "duration_ms", 0) if response else 0,
                intent=None,
                confidence=0.0,
                tokens_used=0,
                extensions_used=[],
            ),
        )
        logger.info(f"=== CHAT REQUEST COMPLETE === Response length: {len(response_content)}")
        return chat_response

    except HTTPException as http_exc:
        logger.error(f"HTTP exception in chat: status={http_exc.status_code}, detail={http_exc.detail}")
        raise
    except Exception as e:
        logger.error(f"=== CHAT REQUEST FAILED ===")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Session: {session_id}")
        logger.error(f"Full traceback:", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get(
    "/stream",
    summary="Stream chat response",
    description="Get real-time streaming response from Sena",
)
async def stream_chat(
    message: str = Query(..., min_length=1),
    session_id: str | None = None,
    sena: Sena = Depends(get_sena),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> StreamingResponse:
    """Stream a chat response in real-time."""
    try:
        if not message or not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        session_id = session_id or str(uuid.uuid4())[:12]

        # Add to memory
        await memory_mgr.add_to_context(content=message, role="user", metadata={"session_id": session_id})

        async def response_generator() -> AsyncGenerator[str, None]:
            """Stream response tokens."""
            try:
                async for chunk in sena.stream(
                    user_input=message,
                ):
                    yield f"data: {chunk}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: ERROR: {str(e)}\n\n"

        return StreamingResponse(
            response_generator(), media_type="text/event-stream", headers={"X-Session-ID": session_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stream setup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/session/title",
    response_model=dict[str, Any],
    summary="Generate a session title",
    description="Use Sena's LLM to generate a short title for a session based on the first user message.",
)
async def generate_session_title(
    request: dict[str, Any],
    sena: Sena = Depends(get_sena),
) -> dict[str, Any]:
    """Generate a concise session title from the opening user message."""
    try:
        message = (request.get("message") or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")

        if not sena.is_initialized:
            raise HTTPException(status_code=503, detail="Sena not initialized")

        from src.llm.prompts.intent_prompts import SESSION_TITLE_PROMPT

        prompt = SESSION_TITLE_PROMPT.format(message=message[:300])

        # Use the LLM manager directly for a quick, low-cost call
        if sena._llm_manager is None:
            raise HTTPException(status_code=503, detail="LLM manager not ready")

        from src.core.constants import ModelType

        response = await sena._llm_manager.generate(
            user_input=prompt,
            model_type=ModelType.FAST,
            max_tokens=20,
            temperature=0.4,
        )

        raw_title = (response.content or "").strip().strip('"').strip("'").strip()
        # Truncate to a sane length
        title = raw_title[:60] if raw_title else "New Session"

        return {"status": "success", "title": title}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session title generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history",
    response_model=dict[str, Any],
    summary="Get conversation history",
    description="Retrieve recent conversation history for a session",
)
async def get_history(
    session_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Get conversation history for a session."""
    try:
        context = await memory_mgr.get_conversation_context(limit=limit)

        return {
            "session_id": session_id or "default",
            "history": context,
            "message_count": len(context.split("\n")) if context else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/clear",
    response_model=dict[str, Any],
    summary="Clear conversation context",
    description="Clear the short-term memory buffer",
)
async def clear_context(
    session_id: str | None = None,
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Clear conversation context for a session."""
    try:
        cleared = await memory_mgr.clear_context()

        return {
            "status": "success",
            "session_id": session_id or "default",
            "items_cleared": cleared,
        }

    except Exception as e:
        logger.error(f"Clear context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
