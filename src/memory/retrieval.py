"""Dynamic memory retrieval engine.

Intelligently decides when and what memories to retrieve based on:
- Intent classification
- Input patterns (temporal references, pronouns, etc)
- User behavior patterns
"""

from typing import Any, Optional

from loguru import logger

from src.memory.embeddings import EmbeddingsHandler
from src.memory.long_term import LongTermMemory
from src.memory.short_term import ShortTermMemory


class RetrievalEngine:
    """Smart memory retrieval that decides when memory is needed."""

    def __init__(self, short_term: ShortTermMemory, long_term: LongTermMemory, embeddings: EmbeddingsHandler):
        """Initialize retrieval engine.

        Args:
            short_term: Short-term memory instance
            long_term: Long-term memory instance
            embeddings: Embeddings handler for semantic search
        """
        self.short_term = short_term
        self.long_term = long_term
        self.embeddings = embeddings

    async def should_retrieve(
        self, user_input: str, intent_type: Optional[str] = None, confidence: float = 0.8
    ) -> bool:
        """Decide if memory retrieval is needed.

        Args:
            user_input: User's input text
            intent_type: Classified intent type
            confidence: Confidence of intent classification

        Returns:
            True if memory should be retrieved
        """
        try:
            # Always retrieve for these intents
            recall_intents = {
                "recall",
                "reference",
                "memory",
                "history",
                "previous",
                "memory_recall",
                "general_conversation",
                "question",
                "complex_query",
                "analysis",
                "summarization",
            }
            if intent_type and intent_type.lower() in recall_intents:
                logger.debug(f"Retrieving due to recall intent: {intent_type}")
                return True

            # Never retrieve for these intents
            skip_intents = {"greeting", "farewell", "help", "settings", "math", "translation"}
            if intent_type and intent_type.lower() in skip_intents:
                logger.debug(f"Skipping retrieval for intent: {intent_type}")
                return False

            user_lower = user_input.lower()

            # --- Explicit memory / recall references ---
            recall_phrases = {
                "remember",
                "recall",
                "forgot",
                "remind me",
                "last time",
                "yesterday",
                "before",
                "previously",
                "earlier",
                "ago",
                "last week",
                "last month",
                "last year",
                "you said",
                "we discussed",
                "you told me",
                "i told you",
                "what did i",
                "what was",
                "what were",
                "what number",
                "what is my",
                "what are my",
                "who is my",
                "do you know my",
                "do you remember",
                "did i tell you",
                "did you know",
                "have i told you",
                "as i mentioned",
                "like i said",
                "previously mentioned",
                "from before",
            }
            for phrase in recall_phrases:
                if phrase in user_lower:
                    logger.debug(f"Retrieving due to recall phrase: '{phrase}'")
                    return True

            # --- Possessive / personal context questions ---
            # "my name", "my birthday", "my job", "my preference" etc.
            personal_patterns = {
                "my name",
                "my age",
                "my job",
                "my work",
                "my company",
                "my email",
                "my phone",
                "my address",
                "my birthday",
                "my preference",
                "my favorite",
                "my colour",
                "my color",
                "my password",
                "my key",
                "my token",
                "my project",
                "my number",
                "my code",
                "my pin",
            }
            for pattern in personal_patterns:
                if pattern in user_lower:
                    logger.debug(f"Retrieving due to personal context pattern: '{pattern}'")
                    return True

            # --- Ambiguous pronouns at the start of the message ---
            ambiguous_pronouns = {"it", "that", "this", "they", "them", "he", "she"}
            words = user_lower.split()
            if words and words[0] in ambiguous_pronouns:
                logger.debug(f"Retrieving due to ambiguous pronoun: '{words[0]}'")
                return True

            # --- Questions in general (for context-aware answers) ---
            if "?" in user_input:
                question_starters = {
                    "what",
                    "who",
                    "where",
                    "when",
                    "why",
                    "how",
                    "which",
                    "whose",
                    "is",
                    "are",
                    "was",
                    "were",
                    "do",
                    "does",
                    "did",
                    "have",
                    "has",
                    "had",
                    "can",
                    "could",
                    "would",
                    "should",
                    "will",
                }
                first_word = words[0] if words else ""
                if first_word in question_starters:
                    logger.debug(f"Retrieving due to question starting with '{first_word}'")
                    return True

            # --- Very short input: likely a continuation ---
            if len(user_input.strip().split()) <= 3:
                logger.debug("Retrieving due to short input (likely continuation)")
                return True

            logger.debug("No retrieval needed")
            return False

        except Exception as e:
            logger.error(f"Error in should_retrieve: {e}")
            return False

    async def retrieve_relevant(self, user_input: str, k: int = 5, include_short_term: bool = True) -> dict[str, Any]:
        """Retrieve relevant memories for user input.

        Args:
            user_input: User's input to find relevant memories for
            k: Number of results
            include_short_term: Include short-term buffer

        Returns:
            Dictionary with short_term and long_term memories
        """
        try:
            result = {"short_term": [], "long_term": [], "retrieval_time": None}

            # Retrieve from short-term buffer (current session context)
            if include_short_term:
                short_term_items = await self.short_term.get_all()
                result["short_term"] = [
                    {"id": item.id, "content": item.content, "role": item.role, "timestamp": item.timestamp.isoformat()}
                    for item in short_term_items
                ]

            # Retrieve from long-term memory
            long_term_memories = await self.long_term.search(query=user_input, k=k)
            result["long_term"] = long_term_memories

            logger.debug(
                f"Retrieved {len(result['short_term'])} short-term and {len(result['long_term'])} long-term memories"
            )

            return result

        except Exception as e:
            logger.error(f"Error retrieving relevant memories: {e}")
            return {"short_term": [], "long_term": [], "error": str(e)}

    async def get_context_for_llm(
        self, user_input: str, intent_type: Optional[str] = None, include_memories: bool = True
    ) -> str:
        """Build context string for LLM including memories.

        Args:
            user_input: User's input
            intent_type: Classified intent
            include_memories: Whether to include retrieved memories

        Returns:
            Formatted context string
        """
        try:
            context_parts = []

            # Add short-term conversation buffer
            short_term_context = await self.short_term.get_context(limit=10)
            if short_term_context:
                context_parts.append("## Recent Conversation:")
                context_parts.append(short_term_context)
                context_parts.append("")

            # Add retrieved memories if needed
            if include_memories:
                should_retrieve = await self.should_retrieve(user_input, intent_type)

                if should_retrieve:
                    memories = await self.retrieve_relevant(user_input, k=5)

                    if memories.get("long_term"):
                        context_parts.append("## Relevant Memories:")
                        for i, memory in enumerate(memories["long_term"], 1):
                            content = memory.get("content", "")[:200]
                            context_parts.append(f"{i}. {content}")
                        context_parts.append("")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error building LLM context: {e}")
            return ""

    async def extract_learnings(self, conversation: str) -> list[str]:
        """Extract key learnings from conversation for storage.

        Args:
            conversation: Full conversation text

        Returns:
            List of extracted learnings to store
        """
        try:
            learnings = []

            # Basic heuristic extraction (production would use LLM)
            lines = conversation.split("\n")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Look for statement patterns
                learning_patterns = {
                    "I learned",
                    "I discovered",
                    "I found",
                    "The key is",
                    "Important:",
                    "Note:",
                    "Remember:",
                    "Key point:",
                    "User mentioned",
                    "User prefers",
                    "User likes",
                    "User dislikes",
                }

                for pattern in learning_patterns:
                    if pattern.lower() in line.lower():
                        learnings.append(line)
                        break

            logger.debug(f"Extracted {len(learnings)} learnings from conversation")
            return learnings

        except Exception as e:
            logger.error(f"Error extracting learnings: {e}")
            return []

    async def store_learnings(self, learnings: list[str], metadata: Optional[dict] = None) -> list[dict[str, Any]]:
        """Store extracted learnings in long-term memory.

        Args:
            learnings: List of learning strings
            metadata: Optional metadata (tags, source, etc)

        Returns:
            List of storage results
        """
        try:
            results = []

            for learning in learnings:
                if not learning or not learning.strip():
                    continue

                # Generate embedding for learning
                embedding = await self.embeddings.generate_embedding(learning)

                # Store in long-term memory
                result = await self.long_term.add(content=learning, metadata=metadata or {}, embedding=embedding)
                results.append(result)

            logger.info(f"Stored {len(results)} learnings in long-term memory")
            return results

        except Exception as e:
            logger.error(f"Error storing learnings: {e}")
            return []

    async def get_retrieval_stats(self) -> dict[str, Any]:
        """Get statistics about memory retrievals.

        Returns:
            Dictionary with retrieval stats
        """
        try:
            return {"short_term": self.short_term.get_stats(), "long_term": await self.long_term.get_stats()}
        except Exception as e:
            logger.error(f"Error getting retrieval stats: {e}")
            return {}
