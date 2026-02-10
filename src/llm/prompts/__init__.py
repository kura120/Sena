# src/llm/prompts/__init__.py
"""Prompt templates for Sena."""

from src.llm.prompts.system_prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_CONCISE,
    SYSTEM_PROMPT_CREATIVE,
    SYSTEM_PROMPT_CODE,
)
from src.llm.prompts.intent_prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    MEMORY_EXTRACTION_PROMPT,
)

__all__ = [
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_CONCISE",
    "SYSTEM_PROMPT_CREATIVE",
    "SYSTEM_PROMPT_CODE",
    "INTENT_CLASSIFICATION_PROMPT",
    "MEMORY_EXTRACTION_PROMPT",
]