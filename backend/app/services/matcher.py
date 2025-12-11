"""Semantic matching service for prompts and pages."""

from typing import List, Optional, Tuple
from uuid import UUID
from dataclasses import dataclass
import re

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embeddings import embedding_service

logger = get_logger(__name__)


@dataclass
class MatchResult:
    """Result of a prompt-page match."""
    page_id: UUID
    similarity_score: float
    match_type: str  # exact, semantic, partial
    matched_snippet: Optional[str]
    rank: int


class MatcherService:
    """Service for matching prompts to pages."""
    
    def __init__(self):
        self.threshold_answered = settings.MATCH_THRESHOLD_ANSWERED
        self.threshold_partial = settings.MATCH_THRESHOLD_PARTIAL
    
    def classify_match_status(self, best_score: Optional[float]) -> str:
        """
        Classify match status based on best similarity score.
        
        Returns:
            One of: answered, partial, gap
        """
        if best_score is None:
            return "gap"
        
        if best_score >= self.threshold_answered:
            return "answered"
        elif best_score >= self.threshold_partial:
            return "partial"
        else:
            return "gap"
    
    def find_matches_in_memory(
        self,
        prompt_embedding: List[float],
        prompt_text: str,
        pages: List[dict],  # List of {id, embedding, content, title}
        top_k: int = 5
    ) -> List[MatchResult]:
        """
        Find matching pages for a prompt using in-memory search.
        
        Args:
            prompt_embedding: Prompt embedding vector
            prompt_text: Original prompt text
            pages: List of page dictionaries with id, embedding, content, title
            top_k: Number of results to return
            
        Returns:
            List of MatchResult objects
        """
        if not pages:
            return []
        
        # Get semantic matches
        page_embeddings = [p["embedding"] for p in pages]
        similar_indices = embedding_service.find_most_similar(
            prompt_embedding, 
            page_embeddings, 
            top_k=top_k * 2  # Get more candidates for filtering
        )
        
        results = []
        
        for rank, (idx, similarity) in enumerate(similar_indices[:top_k], 1):
            page = pages[idx]
            
            # Check for exact keyword match
            exact_match = self._check_exact_match(prompt_text, page.get("content", ""))
            
            # Determine match type
            if exact_match:
                match_type = "exact"
                similarity = max(similarity, 0.85)  # Boost exact matches
            elif similarity >= self.threshold_partial:
                match_type = "semantic"
            else:
                match_type = "partial"
            
            # Extract snippet
            snippet = self._extract_snippet(prompt_text, page.get("content", ""))
            
            results.append(MatchResult(
                page_id=page["id"],
                similarity_score=similarity,
                match_type=match_type,
                matched_snippet=snippet,
                rank=rank
            ))
        
        return results
    
    def _check_exact_match(self, prompt: str, content: str) -> bool:
        """Check if prompt keywords appear in content."""
        if not prompt or not content:
            return False
        
        # Extract key phrases from prompt
        prompt_lower = prompt.lower()
        content_lower = content.lower()
        
        # Remove common words
        stop_words = {"what", "how", "is", "the", "a", "an", "to", "for", "of", "in", "on", "and", "or", "i", "my", "you", "your", "can", "do", "does"}
        words = [w for w in re.findall(r'\w+', prompt_lower) if w not in stop_words and len(w) > 2]
        
        if not words:
            return False
        
        # Check if most key words appear in content
        matches = sum(1 for w in words if w in content_lower)
        return matches >= len(words) * 0.7
    
    def _extract_snippet(self, prompt: str, content: str, max_length: int = 300) -> Optional[str]:
        """Extract relevant snippet from content."""
        if not content:
            return None
        
        # Get key words from prompt
        prompt_lower = prompt.lower()
        words = re.findall(r'\w+', prompt_lower)
        key_words = [w for w in words if len(w) > 3][:5]
        
        if not key_words:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        content_lower = content.lower()
        
        # Find best window containing most keywords
        best_start = 0
        best_score = 0
        window_size = max_length
        
        for i in range(0, len(content) - window_size, 50):
            window = content_lower[i:i + window_size]
            score = sum(1 for w in key_words if w in window)
            if score > best_score:
                best_score = score
                best_start = i
        
        snippet = content[best_start:best_start + max_length]
        
        # Clean up snippet boundaries
        if best_start > 0:
            snippet = "..." + snippet
        if best_start + max_length < len(content):
            snippet = snippet + "..."
        
        return snippet


# Singleton instance
matcher = MatcherService()

