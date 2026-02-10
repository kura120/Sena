# src/core/sena.py (COMPLETE)
"""
Sena Core Orchestrator

The main coordinator that brings together all Sena components:
- LLM management and routing
- Memory system
- Extension execution
- Telemetry and error handling
"""

import asyncio
import re
import time
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Coroutine, Optional

from src.config.settings import get_settings
from src.core.constants import ProcessingStage, ModelType, IntentType
from src.core.error_handler import error_handler, ErrorContext
from src.core.exceptions import SenaException, LLMGenerationError
from src.core.telemetry import get_telemetry, TelemetryCollector
from src.database.connection import get_db, close_db, DatabaseManager
from src.database.models.conversation import Conversation
from src.database.repositories.conversation_repo import ConversationRepository
from src.database.repositories.memory_repo import MemoryRepository
from src.llm.manager import LLMManager
from src.llm.models.base import Message, LLMResponse, MessageRole
from src.llm.router import IntentResult
from src.utils.logger import logger


class ProcessingContext:
    """Context for a single processing request."""
    
    def __init__(
        self,
        session_id: str,
        user_input: str,
    ):
        self.session_id = session_id
        self.user_input = user_input
        self.request_id = str(uuid.uuid4())[:8]
        self.start_time = time.perf_counter()
        self.stage = ProcessingStage.RECEIVING
        
        # Results
        self.intent_result: Optional[IntentResult] = None
        self.memory_context: list[Message] = []
        self.extension_results: dict[str, Any] = {}
        self.response: Optional[LLMResponse] = None
        
        # Timing
        self.stage_times: dict[str, float] = {}
    
    def set_stage(self, stage: ProcessingStage) -> None:
        """Update current processing stage."""
        if self.stage != stage:
            # Record time spent in previous stage
            elapsed = (time.perf_counter() - self.start_time) * 1000
            self.stage_times[self.stage.value] = elapsed
            self.stage = stage
    
    @property
    def elapsed_ms(self) -> float:
        """Get total elapsed time in milliseconds."""
        return (time.perf_counter() - self.start_time) * 1000
    
    def to_error_context(self) -> ErrorContext:
        """Convert to ErrorContext for error handling."""
        return ErrorContext(
            session_id=self.session_id,
            user_input=self.user_input,
            processing_stage=self.stage.value,
            model_used=self.intent_result.recommended_model.value if self.intent_result else None,
        )


class Sena:
    """
    Main Sena orchestrator.
    
    Coordinates all subsystems to process user requests:
    1. Intent classification
    2. Memory retrieval
    3. Extension execution
    4. LLM generation
    5. Post-processing and memory storage
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())[:12]
        self.settings = get_settings()
        
        # Components (initialized later)
        self._llm_manager: Optional[LLMManager] = None
        self._telemetry: Optional[TelemetryCollector] = None
        self._conversation_repo: Optional[ConversationRepository] = None
        self._memory_repo: Optional[MemoryRepository] = None
        self._db: Optional[DatabaseManager] = None
        
        # Callbacks
        self._stage_callback: Optional[Callable[[ProcessingStage, str], Coroutine[Any, Any, None]]] = None
        self._token_callback: Optional[Callable[[str, bool], Coroutine[Any, Any, None]]] = None
        
        # State
        self._initialized = False
        self._message_count = 0
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize(self) -> None:
        """Initialize all Sena components."""
        if self._initialized:
            return
        
        logger.info(f"Initializing Sena (session: {self.session_id})")
        
        try:
            # Initialize database
            self._db = await get_db()
            self._conversation_repo = ConversationRepository(self._db)
            self._memory_repo = MemoryRepository(self._db)
            
            # Initialize LLM manager
            self._llm_manager = LLMManager()
            await self._llm_manager.initialize()
            
            # Set up LLM callbacks
            self._llm_manager.set_stage_callback(self._on_stage_change)
            self._llm_manager.set_token_callback(self._on_token)
            
            # Initialize telemetry
            self._telemetry = await get_telemetry()
            
            # Set up error handler callbacks
            error_handler.set_telemetry_callback(self._on_telemetry_event)
            
            self._initialized = True
            logger.info("Sena initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sena: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown Sena and cleanup resources."""
        logger.info("Shutting down Sena...")
        
        if self._llm_manager:
            await self._llm_manager.shutdown()
        
        if self._telemetry:
            await self._telemetry.shutdown()
        
        await close_db()
        
        self._initialized = False
        logger.info("Sena shutdown complete")
    
    def set_stage_callback(self, callback: Callable[[ProcessingStage, str], Coroutine[Any, Any, None]]) -> None:
        """Set callback for processing stage updates."""
        self._stage_callback = callback
    
    def set_token_callback(self, callback: Callable[[str, bool], Coroutine[Any, Any, None]]) -> None:
        """Set callback for streaming tokens."""
        self._token_callback = callback
    
    async def _on_stage_change(self, stage: ProcessingStage, details: str = "") -> None:
        """Handle stage change notifications."""
        if self._stage_callback:
            await self._stage_callback(stage, details)
    
    async def _on_token(self, token: str, is_final: bool = False) -> None:
        """Handle token stream notifications."""
        if self._token_callback:
            await self._token_callback(token, is_final)
    
    async def _on_telemetry_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle telemetry events from error handler."""
        if self._telemetry:
            await self._telemetry.record_metric(
                f"events.{event_type}",
                1,
                tags=data,
                metric_type="counter",
            )
    
    async def process(
        self,
        user_input: str,
        stream: bool = False,
    ) -> LLMResponse:
        """
        Process a user message and generate a response.
        
        Args:
            user_input: The user's input message
            stream: Whether to stream the response
            
        Returns:
            LLMResponse with generated content
        """
        if not self._initialized:
            raise SenaException("Sena not initialized")
        
        if not self._llm_manager:
            raise SenaException("LLM manager not initialized")
        
        ctx = ProcessingContext(self.session_id, user_input)
        
        try:
            # 1. Classify intent
            ctx.set_stage(ProcessingStage.INTENT_CLASSIFICATION)
            await self._on_stage_change(ctx.stage, "Analyzing intent...")
            
            ctx.intent_result = await self._llm_manager.classify_intent(user_input)
            
            logger.debug(f"Intent: {ctx.intent_result.intent_type.value}, "
                        f"Model: {ctx.intent_result.recommended_model.value}")
            
            # 2. Retrieve memory if needed
            if ctx.intent_result.needs_memory:
                ctx.set_stage(ProcessingStage.MEMORY_RETRIEVAL)
                await self._on_stage_change(ctx.stage, "Retrieving memories...")
                
                ctx.memory_context = await self._retrieve_memory(user_input)
            
            # 3. Check and execute extensions
            if ctx.intent_result.required_extensions:
                ctx.set_stage(ProcessingStage.EXTENSION_EXECUTION)
                await self._on_stage_change(ctx.stage, "Running extensions...")
                
                ctx.extension_results = await self._execute_extensions(
                    ctx.intent_result.required_extensions,
                    user_input,
                )
            
            # 4. Generate response
            if stream:
                # For streaming, we'll accumulate the response
                response_content = ""
                
                async for chunk in self._llm_manager.stream(
                    user_input=user_input,
                    context=ctx.memory_context,
                    model_type=ctx.intent_result.recommended_model,
                ):
                    response_content += chunk.content
                    
                    if chunk.is_final:
                        ctx.response = LLMResponse(
                            content=response_content,
                            model=self.settings.llm.models[ctx.intent_result.recommended_model.value].name,
                            duration_ms=ctx.elapsed_ms,
                        )
            else:
                ctx.set_stage(ProcessingStage.LLM_PROCESSING)
                await self._on_stage_change(ctx.stage, "Generating response...")
                
                ctx.response = await self._llm_manager.generate(
                    user_input=user_input,
                    context=ctx.memory_context,
                    model_type=ctx.intent_result.recommended_model,
                )
            
            # 5. Post-processing
            ctx.set_stage(ProcessingStage.POST_PROCESSING)
            await self._on_stage_change(ctx.stage, "Post-processing...")
            
            await self._post_process(ctx)
            
            # 6. Complete
            ctx.set_stage(ProcessingStage.COMPLETE)
            await self._on_stage_change(ctx.stage, f"Complete ({ctx.elapsed_ms:.0f}ms)")
            
            # Record metrics
            await self._record_metrics(ctx)
            
            if ctx.response is None:
                raise LLMGenerationError("No response generated")
            
            return ctx.response
            
        except Exception as e:
            ctx.set_stage(ProcessingStage.ERROR)
            await self._on_stage_change(ctx.stage, str(e))
            
            # Handle error
            await error_handler.handle(e, ctx.to_error_context(), reraise=True)
            raise  # This line won't be reached but makes type checker happy
    
    async def stream(
        self,
        user_input: str,
    ) -> AsyncIterator[str]:
        """
        Stream a response for user input.
        
        Yields response tokens as they're generated.
        
        Args:
            user_input: The user's input message
            
        Yields:
            Response tokens
        """
        if not self._initialized:
            raise SenaException("Sena not initialized")
        
        if not self._llm_manager:
            raise SenaException("LLM manager not initialized")
        
        ctx = ProcessingContext(self.session_id, user_input)
        
        try:
            # 1. Classify intent
            ctx.set_stage(ProcessingStage.INTENT_CLASSIFICATION)
            ctx.intent_result = await self._llm_manager.classify_intent(user_input)
            
            # 2. Retrieve memory if needed
            if ctx.intent_result.needs_memory:
                ctx.set_stage(ProcessingStage.MEMORY_RETRIEVAL)
                ctx.memory_context = await self._retrieve_memory(user_input)
            
            # 3. Execute extensions
            if ctx.intent_result.required_extensions:
                ctx.set_stage(ProcessingStage.EXTENSION_EXECUTION)
                ctx.extension_results = await self._execute_extensions(
                    ctx.intent_result.required_extensions,
                    user_input,
                )
            
            # 4. Stream response
            ctx.set_stage(ProcessingStage.LLM_STREAMING)
            
            full_response = ""
            
            async for chunk in self._llm_manager.stream(
                user_input=user_input,
                context=ctx.memory_context,
                model_type=ctx.intent_result.recommended_model,
            ):
                full_response += chunk.content
                yield chunk.content
                
                if chunk.is_final:
                    ctx.response = LLMResponse(
                        content=full_response,
                        model=self.settings.llm.models[ctx.intent_result.recommended_model.value].name,
                        duration_ms=ctx.elapsed_ms,
                    )
            
            # 5. Post-processing
            ctx.set_stage(ProcessingStage.POST_PROCESSING)
            await self._post_process(ctx)
            
            # 6. Complete
            ctx.set_stage(ProcessingStage.COMPLETE)
            await self._record_metrics(ctx)
            
        except Exception as e:
            ctx.set_stage(ProcessingStage.ERROR)
            await error_handler.handle(e, ctx.to_error_context(), reraise=True)
            raise
    
    async def _retrieve_memory(self, user_input: str) -> list[Message]:
        """Retrieve relevant memories for context."""
        messages: list[Message] = []
        
        if not self._memory_repo:
            return messages
        
        try:
            # Get short-term memory (recent conversation)
            short_term = await self._memory_repo.short_term.get_session_buffer(
                self.session_id,
                limit=self.settings.memory.short_term.max_messages,
            )
            
            for mem in short_term:
                role = MessageRole.USER if mem.role == "user" else MessageRole.ASSISTANT
                messages.append(Message(
                    role=role,
                    content=mem.content,
                ))
            
            session_ref = self._extract_session_reference(user_input)
            metadata_filter = {"session_id": session_ref} if session_ref else None

            try:
                from src.memory.manager import MemoryManager

                mem_mgr = MemoryManager.get_instance()
                long_term = await mem_mgr.long_term.search(
                    query=user_input,
                    k=5,
                    metadata_filter=metadata_filter,
                )
                if long_term:
                    header = "Relevant memories"
                    if session_ref:
                        header = f"Relevant memories from {session_ref}"
                    memory_lines = [header + ":"]
                    for idx, memory in enumerate(long_term, 1):
                        memory_lines.append(f"{idx}. {memory.get('content', '')}")
                    messages.append(Message(role=MessageRole.SYSTEM, content="\n".join(memory_lines)))
            except Exception as e:
                logger.warning(f"Long-term memory retrieval error: {e}")
            
        except Exception as e:
            logger.warning(f"Memory retrieval error: {e}")
        
        return messages

    def _extract_session_reference(self, user_input: str) -> Optional[str]:
        match = re.search(r"session\s*#?\s*(\d+)", user_input.lower())
        if match:
            return f"session-{match.group(1)}"
        return None
    
    async def _execute_extensions(
        self,
        extension_names: list[str],
        user_input: str,
    ) -> dict[str, Any]:
        """Execute required extensions."""
        results: dict[str, Any] = {}
        
        # TODO: Implement extension execution
        # For now, return empty results
        
        for ext_name in extension_names:
            logger.debug(f"Would execute extension: {ext_name}")
            results[ext_name] = None
        
        return results
    
    async def _post_process(self, ctx: ProcessingContext) -> None:
        """Post-process the response."""
        if not ctx.response:
            return
        
        # Store conversation
        try:
            if self._conversation_repo:
                conversation = Conversation(
                    session_id=self.session_id,
                    user_input=ctx.user_input,
                    sena_response=ctx.response.content,
                    model_used=ctx.response.model,
                    processing_time_ms=ctx.elapsed_ms,
                    intent_type=ctx.intent_result.intent_type.value if ctx.intent_result else None,
                    metadata={
                        "request_id": ctx.request_id,
                        "stage_times": ctx.stage_times,
                    },
                )
                
                await self._conversation_repo.create(conversation)
            
            # Update short-term memory
            if self._memory_repo:
                await self._memory_repo.short_term.add_message(
                    session_id=self.session_id,
                    content=ctx.user_input,
                    role="user",
                )
                
                await self._memory_repo.short_term.add_message(
                    session_id=self.session_id,
                    content=ctx.response.content,
                    role="assistant",
                )
            
        except Exception as e:
            logger.warning(f"Failed to store conversation: {e}")
        
        # Update message count
        self._message_count += 1
        
        # Extract long-term memories periodically
        if self._message_count % self.settings.memory.long_term.extract_interval == 0:
            # TODO: Implement memory extraction
            logger.debug("Would extract long-term memories")
    
    async def _record_metrics(self, ctx: ProcessingContext) -> None:
        """Record telemetry metrics for the request."""
        if not self._telemetry:
            return
        
        # Total processing time
        await self._telemetry.record_histogram(
            "sena.request.duration_ms",
            ctx.elapsed_ms,
            tags={"intent": ctx.intent_result.intent_type.value if ctx.intent_result else "unknown"},
        )
        
        # Model used
        if ctx.intent_result:
            await self._telemetry.increment_counter(
                f"sena.model.{ctx.intent_result.recommended_model.value}.requests",
            )
        
        # Request count
        await self._telemetry.increment_counter("sena.requests.total")
    
    async def get_conversation_history(
        self,
        limit: int = 50,
    ) -> list[Conversation]:
        """Get conversation history for this session."""
        if not self._conversation_repo:
            return []
        
        return await self._conversation_repo.get_by_session(
            self.session_id,
            limit=limit,
        )
    
    async def clear_short_term_memory(self) -> None:
        """Clear short-term memory for this session."""
        if self._memory_repo:
            await self._memory_repo.short_term.clear_session(self.session_id)
            logger.info(f"Cleared short-term memory for session {self.session_id}")
    
    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        stats: dict[str, Any] = {
            "session_id": self.session_id,
            "message_count": self._message_count,
            "initialized": self._initialized,
        }
        
        if self._llm_manager:
            stats["llm"] = self._llm_manager.get_stats()
        
        return stats