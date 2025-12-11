"""Azure OpenAI service for enhanced NLP capabilities."""

import json
from typing import Optional, List, Dict, Any
from openai import AzureOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AzureOpenAIService:
    """Service for Azure OpenAI API calls."""
    
    def __init__(self):
        self.enabled = bool(settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_KEY)
        self.client = None
        
        if self.enabled:
            try:
                self.client = AzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_KEY,
                    api_version=settings.AZURE_API_VERSION,
                )
                logger.info("Azure OpenAI service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI: {e}")
                self.enabled = False
    
    def classify_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Use GPT-4o to classify intent with detailed reasoning.
        
        Returns dict with:
        - intent: The classified intent type
        - confidence: Confidence score (0-1)
        - reasoning: Why this classification was chosen
        - transaction_score: Likelihood of transaction (0-1)
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=settings.AZURE_COMPLETION_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at classifying search query intent. Analyze the query and classify it into one of these categories:

INTENT TYPES:
- transactional: User wants to buy, book, subscribe, or complete an action (e.g., "Book a flight to NYC")
- commercial: User is researching before purchase, comparing options (e.g., "Best airlines for transatlantic")
- comparison: Explicitly comparing two or more options (e.g., "Virgin vs British Airways")
- informational: User wants to learn or understand something (e.g., "What is baggage allowance?")
- navigational: User wants to go to a specific page/service (e.g., "Virgin Atlantic login")
- procedural: User wants step-by-step instructions (e.g., "How to upgrade my seat")
- troubleshooting: User has a problem to solve (e.g., "My booking isn't showing")
- opinion_seeking: User wants subjective opinions (e.g., "Is Premium Economy worth it?")
- regulatory: User asking about rules/policies (e.g., "EU261 compensation rules")
- exploratory: General browsing without specific goal (e.g., "Tell me about Virgin lounges")
- emotional: User expressing sentiment (e.g., "The flight was amazing")
- brand_monitoring: Asking about brand news/mentions (e.g., "What did reviews say about...")
- meta: Asking for content generation (e.g., "Write a review about...")

Respond with JSON only:
{
  "intent": "the_intent_type",
  "confidence": 0.0-1.0,
  "transaction_score": 0.0-1.0,
  "reasoning": "Brief explanation of why this classification"
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Classify this query: \"{text}\""
                    }
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"LLM intent classification: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Azure OpenAI intent classification failed: {e}")
            return None
    
    def generate_content_suggestion(
        self, 
        prompt_text: str, 
        intent: str,
        match_status: str,
        existing_content_snippets: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate specific content suggestions for addressing a prompt.
        
        Returns dict with:
        - title: Suggested content title
        - content_type: article, faq, landing_page, etc.
        - outline: Key points to cover
        - cta_suggestion: Call-to-action recommendation
        - seo_keywords: Relevant keywords
        """
        if not self.enabled or not self.client:
            return None
        
        existing_context = ""
        if existing_content_snippets:
            existing_context = f"\n\nExisting content snippets:\n" + "\n---\n".join(existing_content_snippets[:3])
        
        try:
            response = self.client.chat.completions.create(
                model=settings.AZURE_COMPLETION_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a content strategist. Based on a user query and its intent, suggest specific content to create or improve.

Consider:
- The user's search intent (what they're trying to accomplish)
- Whether this is a gap (no content) or partial match (needs improvement)
- SEO best practices
- Conversion optimization for transactional queries

Respond with JSON only:
{
  "title": "Suggested page/article title",
  "content_type": "article|faq|landing_page|comparison|how_to|policy",
  "outline": ["Key point 1", "Key point 2", "Key point 3"],
  "cta_suggestion": "Recommended call-to-action",
  "seo_keywords": ["keyword1", "keyword2"],
  "priority_reason": "Why this content is valuable"
}"""
                    },
                    {
                        "role": "user",
                        "content": f"""Query: "{prompt_text}"
Intent: {intent}
Match Status: {match_status}
{existing_context}

Generate content suggestion:"""
                    }
                ],
                temperature=0.3,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"LLM content suggestion: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Azure OpenAI content suggestion failed: {e}")
            return None
    
    def analyze_content_gap(
        self,
        prompt_text: str,
        page_content: str,
        match_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze why content doesn't fully match a query.
        
        Returns dict with:
        - gap_reason: Why the content doesn't fully address the query
        - missing_elements: What's missing from the content
        - improvement_suggestions: Specific ways to improve
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=settings.AZURE_COMPLETION_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze why existing content doesn't fully address a user's query. Be specific and actionable.

Respond with JSON only:
{
  "gap_reason": "Brief explanation of the mismatch",
  "missing_elements": ["Missing element 1", "Missing element 2"],
  "improvement_suggestions": ["Suggestion 1", "Suggestion 2"],
  "estimated_effort": "low|medium|high"
}"""
                    },
                    {
                        "role": "user",
                        "content": f"""User Query: "{prompt_text}"
Match Score: {match_score * 100:.0f}%

Existing Content (excerpt):
{page_content[:1500]}

Analyze the gap:"""
                    }
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Azure OpenAI gap analysis failed: {e}")
            return None


# Singleton instance
azure_openai_service = AzureOpenAIService()

