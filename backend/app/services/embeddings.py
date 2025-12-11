"""Embedding generation service using sentence-transformers."""

from typing import List, Optional
import numpy as np
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy load the model to avoid startup delay
_model = None


def get_embedding_model():
    """Get or initialize the embedding model (lazy loading)."""
    global _model
    if _model is None:
        logger.info("Loading embedding model", model=settings.EMBEDDING_MODEL)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded", dimension=settings.EMBEDDING_DIMENSION)
    return _model


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model = None
    
    @property
    def model(self):
        """Lazy-load the model."""
        if self._model is None:
            self._model = get_embedding_model()
        return self._model
    
    def encode(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to encode
            
        Returns:
            List of floats representing the embedding
        """
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e), text=text[:100])
            return [0.0] * self.dimension
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            
        Returns:
            List of embeddings
        """
        if not texts:
            return []
        
        # Filter empty texts
        clean_texts = [t.strip() if t else "" for t in texts]
        
        try:
            embeddings = self.model.encode(
                clean_texts, 
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=len(texts) > 100
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error("Failed to generate batch embeddings", error=str(e))
            return [[0.0] * self.dimension for _ in texts]
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Normalize to 0-1 range (cosine can be -1 to 1)
            return float((similarity + 1) / 2)
            
        except Exception as e:
            logger.error("Failed to calculate similarity", error=str(e))
            return 0.0
    
    def find_most_similar(
        self, 
        query_embedding: List[float], 
        candidate_embeddings: List[List[float]], 
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar embeddings from candidates.
        
        Args:
            query_embedding: Query vector
            candidate_embeddings: List of candidate vectors
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
        """
        if not candidate_embeddings:
            return []
        
        try:
            query_vec = np.array(query_embedding)
            candidates_matrix = np.array(candidate_embeddings)
            
            # Calculate all similarities at once
            dot_products = np.dot(candidates_matrix, query_vec)
            norms_candidates = np.linalg.norm(candidates_matrix, axis=1)
            norm_query = np.linalg.norm(query_vec)
            
            # Avoid division by zero
            with np.errstate(divide='ignore', invalid='ignore'):
                similarities = dot_products / (norms_candidates * norm_query)
                similarities = np.nan_to_num(similarities, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Normalize to 0-1
            similarities = (similarities + 1) / 2
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            return [(int(idx), float(similarities[idx])) for idx in top_indices]
            
        except Exception as e:
            logger.error("Failed to find similar embeddings", error=str(e))
            return []


# Singleton instance
embedding_service = EmbeddingService()

