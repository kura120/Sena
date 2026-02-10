"""Embeddings handler for vector representations of memories."""

from typing import Optional
import numpy as np
from loguru import logger


class EmbeddingsHandler:
    """Generate and manage embeddings for semantic search."""

    def __init__(self, model_name: str = "nomic-embed-text:latest"):
        """Initialize embeddings handler.
        
        Args:
            model_name: The embedding model to use (from Ollama)
        """
        self.model_name = model_name
        self.dimension = 768  # Default for nomic-embed-text

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding, or None on error
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return None

            # Import here to avoid circular imports
            from src.llm.manager import LLMManager
            
            llm_manager = LLMManager()
            
            # Use Ollama embedding endpoint
            embedding = await llm_manager.get_embeddings(
                text=text,
                model_name=self.model_name
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def generate_batch_embeddings(
        self,
        texts: list[str]
    ) -> list[Optional[list[float]]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (may contain None for failed items)
        """
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def calculate_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score between 0 and 1
        """
        if not embedding1 or not embedding2:
            return 0.0

        try:
            a = np.array(embedding1)
            b = np.array(embedding2)
            
            similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            return float(max(0.0, min(1.0, similarity)))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def find_most_similar(
        self,
        query_embedding: list[float],
        candidate_embeddings: list[tuple[str, list[float]]]
    ) -> list[tuple[str, float]]:
        """Find most similar embeddings from candidates.
        
        Args:
            query_embedding: The query embedding
            candidate_embeddings: List of (id, embedding) tuples
            
        Returns:
            List of (id, similarity_score) sorted by similarity descending
        """
        similarities = []
        
        for item_id, embedding in candidate_embeddings:
            similarity = self.calculate_similarity(query_embedding, embedding)
            similarities.append((item_id, similarity))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities
