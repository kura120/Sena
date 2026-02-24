# src/llm/router.py
"""
Intent Router

Classifies user intent and routes to appropriate model.
Uses function-calling capable model for classification.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.core.constants import (
    INTENT_EXTENSION_MAPPING,
    INTENT_MODEL_MAPPING,
    INTENT_NEEDS_MEMORY,
    IntentType,
    ModelType,
)
from src.llm.models.base import Message
from src.llm.models.model_registry import ModelRegistry
from src.llm.prompts.intent_prompts import INTENT_CLASSIFICATION_PROMPT
from src.utils.logger import logger


@dataclass
class IntentResult:
    """
    Result of intent classification.

    Attributes:
        intent_type: Classified intent type
        recommended_model: Recommended model for this intent
        required_extensions: Extensions needed for this intent
        needs_memory: Whether memory retrieval is recommended
        confidence: Classification confidence (0-1)
        raw_response: Raw response from classifier
    """

    intent_type: IntentType
    recommended_model: ModelType
    required_extensions: list[str] = field(default_factory=list)
    needs_memory: bool = False
    confidence: float = 1.0
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent_type": self.intent_type.value,
            "recommended_model": self.recommended_model.value,
            "required_extensions": self.required_extensions,
            "needs_memory": self.needs_memory,
            "confidence": self.confidence,
        }


class IntentRouter:
    """
    Routes user input to appropriate model based on intent.

    Uses a lightweight model for fast intent classification,
    then maps intent to the best model for handling.
    """

    # How many consecutive load failures before the circuit opens
    _CIRCUIT_FAILURE_THRESHOLD: int = 3
    # How long (seconds) to keep the circuit open before retrying
    _CIRCUIT_COOLDOWN: float = 300.0  # 5 minutes

    def __init__(self) -> None:
        self._registry: Optional[ModelRegistry] = None
        self._initialized = False

        # Circuit breaker state for the router model
        self._router_failure_count: int = 0
        self._router_circuit_open_until: float = 0.0  # monotonic timestamp

        # Keywords for quick classification without LLM
        self._greeting_keywords = {
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "howdy",
            "greetings",
            "yo",
            "sup",
        }

        self._farewell_keywords = {
            "bye",
            "goodbye",
            "see you",
            "later",
            "farewell",
            "good night",
            "take care",
            "cya",
            "gtg",
        }

        self._code_keywords = {
            "code",
            "program",
            "function",
            "class",
            "implement",
            "write",
            "create",
            "build",
            "develop",
            "script",
            "python",
            "javascript",
            "java",
            "c++",
            "rust",
            "debug",
            "fix",
            "error",
            "bug",
        }

        self._memory_indicators = {
            "remember",
            "recall",
            "last time",
            "previously",
            "before",
            "earlier",
            "you said",
            "we discussed",
            "mentioned",
            "told you",
            "forgot",
        }

        self._file_keywords = {
            "file",
            "files",
            "folder",
            "folders",
            "directory",
            "directories",
            "downloads",
            "desktop",
            "documents",
            "path",
            "filename",
        }

        self._file_action_keywords = {
            "find",
            "search",
            "locate",
            "check",
            "look for",
            "exists",
            "is there",
            "do i have",
            "in my",
        }

    async def initialize(self, registry: ModelRegistry) -> None:
        """Initialize the router with model registry."""
        self._registry = registry
        self._initialized = True
        logger.info("Intent router initialized")

    async def classify(self, user_input: str) -> IntentResult:
        """
        Classify user intent.

        Uses a multi-step approach:
        1. Quick keyword-based classification for obvious cases
        2. LLM-based classification for complex cases

        Args:
            user_input: The user's input message

        Returns:
            IntentResult with classification details
        """
        # Normalize input
        input_lower = user_input.lower().strip()

        # Try quick classification first
        quick_result = self._quick_classify(input_lower)
        if quick_result:
            return quick_result

        # Use LLM for complex classification
        if self._registry and self._initialized:
            return await self._llm_classify(user_input)

        # Fallback to general conversation
        return self._create_result(IntentType.GENERAL_CONVERSATION, confidence=0.5)

    def _quick_classify(self, input_lower: str) -> Optional[IntentResult]:
        """
        Attempt quick classification using keywords.

        Args:
            input_lower: Lowercase user input

        Returns:
            IntentResult if confident, None otherwise
        """
        words = set(input_lower.split())

        # Check greetings (very short input with greeting words)
        if len(words) <= 3:
            for keyword in self._greeting_keywords:
                if keyword in input_lower:
                    return self._create_result(IntentType.GREETING, confidence=0.95)

        # Check farewells
        for keyword in self._farewell_keywords:
            if keyword in input_lower:
                return self._create_result(IntentType.FAREWELL, confidence=0.9)

        # Check code-related
        code_matches = sum(1 for kw in self._code_keywords if kw in input_lower)
        if code_matches >= 2:
            # Determine if it's code request or explanation
            if any(kw in input_lower for kw in ["explain", "what does", "how does", "understand"]):
                return self._create_result(IntentType.CODE_EXPLANATION, confidence=0.85)
            return self._create_result(IntentType.CODE_REQUEST, confidence=0.85)

        # Check memory-related
        for indicator in self._memory_indicators:
            if indicator in input_lower:
                return self._create_result(IntentType.MEMORY_RECALL, confidence=0.9)

        # Check file operations
        if any(kw in input_lower for kw in self._file_keywords) and any(
            action in input_lower for action in self._file_action_keywords
        ):
            return self._create_result(IntentType.FILE_OPERATION, confidence=0.85)

        # Check for questions
        if input_lower.endswith("?") or input_lower.startswith(
            ("what", "who", "where", "when", "why", "how", "is", "are", "can", "could", "would", "should")
        ):
            # Determine complexity
            if len(input_lower) > 100 or any(
                kw in input_lower for kw in ["analyze", "compare", "explain why", "in depth"]
            ):
                return self._create_result(IntentType.COMPLEX_QUERY, confidence=0.8)
            return self._create_result(IntentType.QUESTION, confidence=0.8)

        # No confident quick classification
        return None

    async def _llm_classify(self, user_input: str) -> IntentResult:
        """
        Use LLM for intent classification.

        Args:
            user_input: The user's input message

        Returns:
            IntentResult from LLM classification
        """
        if self._registry is None:
            return self._create_result(IntentType.GENERAL_CONVERSATION, confidence=0.3)

        try:
            # Get router model
            router_model = self._registry.get_model(ModelType.ROUTER)

            # Circuit breaker: if the router model has failed too many times
            # recently, skip straight to the fast model instead of blocking.
            circuit_open = time.monotonic() < self._router_circuit_open_until

            if not router_model or circuit_open:
                if circuit_open:
                    logger.debug("Router model circuit open — using fast model for classification")
                else:
                    logger.warning("Router model not available, using fast model")
                router_model = self._registry.get_model(ModelType.FAST)
                if not router_model:
                    return self._create_result(IntentType.GENERAL_CONVERSATION, confidence=0.3)
            elif not router_model.is_loaded:
                try:
                    await router_model.load()
                    # Successful load — reset circuit breaker
                    self._router_failure_count = 0
                except Exception as load_err:
                    self._router_failure_count += 1
                    logger.warning(
                        f"Router model load failed ({self._router_failure_count}/"
                        f"{self._CIRCUIT_FAILURE_THRESHOLD}): {load_err}"
                    )
                    if self._router_failure_count >= self._CIRCUIT_FAILURE_THRESHOLD:
                        self._router_circuit_open_until = time.monotonic() + self._CIRCUIT_COOLDOWN
                        logger.warning(
                            f"Router model circuit opened for "
                            f"{self._CIRCUIT_COOLDOWN:.0f}s — "
                            "all classification will use fast model until then"
                        )
                    # Fall back to fast model for this request
                    router_model = self._registry.get_model(ModelType.FAST)
                    if not router_model:
                        return self._create_result(IntentType.GENERAL_CONVERSATION, confidence=0.3)

            # Build classification prompt
            prompt = INTENT_CLASSIFICATION_PROMPT.format(user_input=user_input)

            # Get classification
            response = await router_model.generate(
                messages=[Message.user(prompt)],
                max_tokens=50,
                temperature=0.1,
            )

            # Parse response
            intent_str = response.content.strip().lower().replace("_", "-").replace(" ", "_")

            # Match to IntentType
            for intent_type in IntentType:
                if intent_type.value.replace("_", "-") == intent_str or intent_type.value == intent_str:
                    return self._create_result(
                        intent_type,
                        confidence=0.9,
                        raw_response=response.content,
                    )

            # Try partial match
            for intent_type in IntentType:
                if intent_type.value in intent_str or intent_str in intent_type.value:
                    return self._create_result(
                        intent_type,
                        confidence=0.7,
                        raw_response=response.content,
                    )

            # Default to general conversation
            return self._create_result(
                IntentType.GENERAL_CONVERSATION,
                confidence=0.5,
                raw_response=response.content,
            )

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}, using fallback")
            return self._create_result(IntentType.GENERAL_CONVERSATION, confidence=0.3)

    def _create_result(
        self,
        intent_type: IntentType,
        confidence: float = 1.0,
        raw_response: str = "",
    ) -> IntentResult:
        """
        Create an IntentResult with all derived properties.

        Args:
            intent_type: The classified intent
            confidence: Classification confidence
            raw_response: Raw LLM response if applicable

        Returns:
            Complete IntentResult
        """
        return IntentResult(
            intent_type=intent_type,
            recommended_model=INTENT_MODEL_MAPPING.get(intent_type, ModelType.FAST),
            required_extensions=INTENT_EXTENSION_MAPPING.get(intent_type, []),
            needs_memory=INTENT_NEEDS_MEMORY.get(intent_type, True),
            confidence=confidence,
            raw_response=raw_response,
        )

    def get_model_for_intent(self, intent_type: IntentType) -> ModelType:
        """Get the recommended model for an intent type."""
        return INTENT_MODEL_MAPPING.get(intent_type, ModelType.FAST)

    def get_extensions_for_intent(self, intent_type: IntentType) -> list[str]:
        """Get required extensions for an intent type."""
        return INTENT_EXTENSION_MAPPING.get(intent_type, [])

    def intent_needs_memory(self, intent_type: IntentType) -> bool:
        """Check if intent requires memory retrieval."""
        return INTENT_NEEDS_MEMORY.get(intent_type, True)
