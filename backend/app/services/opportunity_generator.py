"""Service for generating and scoring opportunities."""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OpportunityData:
    """Data for creating an opportunity."""
    priority_score: float
    recommended_action: str
    reason: str
    difficulty_score: float
    difficulty_factors: Dict[str, Any]


# Priority weights
WEIGHT_POPULARITY = 0.4
WEIGHT_TRANSACTION = 0.3
WEIGHT_SENTIMENT = 0.2
WEIGHT_DIFFICULTY = 0.1


class OpportunityGenerator:
    """Service for generating opportunities from gap analysis."""
    
    def __init__(self):
        self.transactional_threshold = settings.TRANSACTIONAL_THRESHOLD
    
    def generate_opportunity(
        self,
        prompt_text: str,
        topic: Optional[str],
        popularity_score: Optional[float],
        transaction_score: float,
        sentiment_score: Optional[float],
        match_status: str,
        best_match_score: Optional[float],
        has_related_pages: bool = False,
    ) -> OpportunityData:
        """
        Generate an opportunity with priority scoring and recommendations.
        
        Args:
            prompt_text: The prompt text
            topic: Topic/category
            popularity_score: Normalized popularity (0-1)
            transaction_score: Transaction intent score (0-1)
            sentiment_score: Sentiment (-1 to 1)
            match_status: Current match status (gap, partial, answered)
            best_match_score: Best similarity score if any
            has_related_pages: Whether related pages exist
            
        Returns:
            OpportunityData with scoring and recommendations
        """
        # Estimate difficulty
        difficulty_score, difficulty_factors = self._estimate_difficulty(
            match_status, 
            has_related_pages,
            prompt_text,
            best_match_score
        )
        
        # Calculate priority score
        pop_score = popularity_score or 0.5
        sent_impact = abs(sentiment_score) if sentiment_score else 0.0
        
        priority_score = (
            WEIGHT_POPULARITY * pop_score +
            WEIGHT_TRANSACTION * transaction_score +
            WEIGHT_SENTIMENT * sent_impact -
            WEIGHT_DIFFICULTY * difficulty_score
        )
        
        # Clamp to 0-1
        priority_score = max(0.0, min(1.0, priority_score))
        
        # Determine recommended action
        action, reason = self._recommend_action(
            transaction_score,
            match_status,
            has_related_pages,
            topic,
            prompt_text
        )
        
        return OpportunityData(
            priority_score=priority_score,
            recommended_action=action,
            reason=reason,
            difficulty_score=difficulty_score,
            difficulty_factors=difficulty_factors,
        )
    
    def _estimate_difficulty(
        self, 
        match_status: str, 
        has_related_pages: bool,
        prompt_text: str,
        best_match_score: Optional[float] = None
    ) -> tuple:
        """Estimate difficulty of addressing this opportunity."""
        prompt_lower = prompt_text.lower()
        
        factors = {
            "needs_new_page": match_status == "gap" and not has_related_pages,
            "technical_complexity": 0.0,
            "content_complexity": 0.0,
            "research_required": 0.0,
            "translation_needed": False,
        }
        
        # New page vs updating existing - base difficulty
        if factors["needs_new_page"]:
            factors["technical_complexity"] = 0.6
        elif match_status == "gap":
            factors["technical_complexity"] = 0.4  # Gap but has related pages
        elif match_status == "partial":
            # The lower the match score, the more work needed
            if best_match_score:
                factors["technical_complexity"] = 0.4 - (best_match_score * 0.3)
            else:
                factors["technical_complexity"] = 0.25
        
        # Estimate content complexity based on prompt characteristics
        word_count = len(prompt_text.split())
        
        # Longer questions often need more comprehensive answers
        if word_count > 15:
            factors["content_complexity"] = 0.5
        elif word_count > 10:
            factors["content_complexity"] = 0.35
        elif word_count > 6:
            factors["content_complexity"] = 0.25
        else:
            factors["content_complexity"] = 0.15
        
        # Questions requiring specific/precise information are harder
        precision_keywords = ["how much", "how many", "price", "cost", "exact", "specific", 
                            "requirements", "deadline", "limit", "minimum", "maximum"]
        if any(kw in prompt_lower for kw in precision_keywords):
            factors["research_required"] = 0.3
        
        # Comparison questions require research
        comparison_keywords = ["better", "best", "compare", "vs", "difference", "which"]
        if any(kw in prompt_lower for kw in comparison_keywords):
            factors["research_required"] = max(factors["research_required"], 0.35)
        
        # Technical questions are harder
        technical_keywords = ["api", "integration", "technical", "developer", "code", "sdk", 
                            "policy", "regulation", "passport", "visa", "requirement"]
        if any(kw in prompt_lower for kw in technical_keywords):
            factors["technical_complexity"] += 0.15
        
        # Questions about rules/policies need accuracy
        policy_keywords = ["can i", "am i allowed", "is it possible", "do i need", "what happens if"]
        if any(kw in prompt_lower for kw in policy_keywords):
            factors["research_required"] = max(factors["research_required"], 0.25)
        
        # Calculate overall difficulty with varied weighting
        difficulty = (
            0.25 * (1.0 if factors["needs_new_page"] else 0.0) +
            0.30 * factors["technical_complexity"] +
            0.25 * factors["content_complexity"] +
            0.20 * factors["research_required"]
        )
        
        return min(1.0, max(0.1, difficulty)), factors
    
    def _recommend_action(
        self,
        transaction_score: float,
        match_status: str,
        has_related_pages: bool,
        topic: Optional[str],
        prompt_text: str
    ) -> tuple:
        """Determine recommended action and reason."""
        prompt_lower = prompt_text.lower()
        
        # High transaction intent prompts
        if transaction_score >= self.transactional_threshold:
            if match_status == "gap":
                if "price" in prompt_lower or "cost" in prompt_lower or "rate" in prompt_lower:
                    return "create_product_page", "High purchase intent query about pricing needs dedicated pricing/product page with clear CTAs"
                else:
                    return "create_landing_page", "High purchase intent query needs conversion-focused landing page"
            else:
                return "add_cta", "Partial match exists - add or improve call-to-action for conversion"
        
        # FAQ-style questions
        if any(prompt_lower.startswith(q) for q in ["what is", "what are", "what does", "how do", "how to", "can i", "is there"]):
            if match_status == "gap":
                return "create_faq", "Common question not answered - add to FAQ or help content"
            else:
                return "expand_existing", "Question partially answered - expand existing content"
        
        # Informational content
        if match_status == "gap":
            if has_related_pages:
                return "expand_existing", "Related content exists - expand to cover this topic"
            else:
                return "create_article", "No related content - create new informational article"
        
        # Partial matches
        if match_status == "partial":
            return "expand_existing", "Content partially addresses query - needs expansion"
        
        return "other", "Review and determine best approach"
    
    def calculate_batch_priorities(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Recalculate priorities for a batch, applying relative ranking.
        """
        if not opportunities:
            return []
        
        # Sort by raw priority
        sorted_opps = sorted(
            opportunities, 
            key=lambda x: x.get("priority_score", 0), 
            reverse=True
        )
        
        # Assign percentile ranks
        n = len(sorted_opps)
        for i, opp in enumerate(sorted_opps):
            opp["priority_rank"] = i + 1
            opp["priority_percentile"] = (n - i) / n
        
        return sorted_opps


# Singleton instance
opportunity_generator = OpportunityGenerator()

