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


    def analyze_competitive_position(
        self,
        prompt_text: str,
        transaction_score: float,
        our_content: Dict[str, str],  # {url, title, snippet}
        competitor_results: List[Dict[str, str]],  # [{url, title, snippet}, ...]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze competitive position for a high-intent transactional query.
        
        Returns dict with:
        - competitive_gap: What competitors offer that we don't
        - our_strengths: What we do well
        - recommendations: Specific actions to improve
        - priority: high/medium/low based on transaction potential
        """
        if not self.enabled or not self.client:
            return None
        
        our_info = f"URL: {our_content.get('url', 'N/A')}\nTitle: {our_content.get('title', 'N/A')}\nContent: {our_content.get('snippet', 'N/A')[:500]}"
        
        competitor_info = ""
        for i, comp in enumerate(competitor_results[:5], 1):
            competitor_info += f"\n{i}. {comp.get('title', 'N/A')}\n   URL: {comp.get('url', 'N/A')}\n   Snippet: {comp.get('snippet', 'N/A')[:300]}\n"
        
        try:
            response = self.client.chat.completions.create(
                model=settings.AZURE_COMPLETION_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a competitive analysis expert. Analyze a high-intent transactional search query and compare a website's content against competitors.

Focus on:
- What features/offers competitors highlight that could win the customer
- Pricing, promotions, or urgency tactics used
- Trust signals and social proof
- Call-to-action effectiveness
- Content gaps that could lose the sale

Respond with JSON only:
{
  "competitive_gap": ["Gap 1 - what competitors offer that we lack", "Gap 2", ...],
  "our_strengths": ["Strength 1 - what we do well", "Strength 2", ...],
  "top_competitor": "Name/URL of strongest competitor",
  "competitor_advantages": ["What makes them strong", ...],
  "recommendations": [
    {"action": "Specific action to take", "impact": "high|medium|low", "effort": "low|medium|high"},
    ...
  ],
  "content_suggestions": "Specific content/copy improvements to add",
  "cta_recommendation": "Suggested call-to-action to increase conversion",
  "priority": "high|medium|low"
}"""
                    },
                    {
                        "role": "user",
                        "content": f"""Search Query: "{prompt_text}"
Transaction Likelihood: {transaction_score * 100:.0f}%

OUR CONTENT:
{our_info}

COMPETITOR RESULTS:
{competitor_info}

Analyze competitive position and provide actionable recommendations:"""
                    }
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"LLM competitive analysis: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Azure OpenAI competitive analysis failed: {e}")
            return None

    def generate_prompt_suggestion(
        self,
        page_url: str,
        page_title: str,
        page_content: str,
        meta_description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a suggested search prompt/query for an orphan page.
        
        This helps identify what user queries this content could answer.
        
        Returns dict with:
        - suggested_prompts: List of 3-5 queries this page could answer
        - primary_intent: The main intent this page serves
        - target_audience: Who would search for this
        - content_summary: Brief summary of what the page offers
        """
        if not self.enabled or not self.client:
            return None
        
        content_excerpt = page_content[:2000] if page_content else ""
        meta_info = f"\nMeta Description: {meta_description}" if meta_description else ""
        
        try:
            response = self.client.chat.completions.create(
                model=settings.AZURE_COMPLETION_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an SEO and content strategist. Given a webpage, generate NATURAL search queries that real users would type or speak.

IMPORTANT - Generate queries as REAL QUESTIONS that humans ask:
- Start with: "How", "What", "Where", "When", "Why", "Which", "Can I", "Is it", "Are there", "Do I need"
- Make them conversational and specific
- Think about what someone would ask Google, Siri, or ChatGPT
- Include buying-intent questions for commercial pages (e.g., "What's the best...", "How much does... cost")

BAD examples (too keyword-focused):
- "Italy cruise packages 2025"
- "cruise deals Mediterranean"

GOOD examples (natural questions):
- "What are the best cruise destinations in Italy?"
- "How much does a Mediterranean cruise cost in 2025?"
- "Where can I book a cruise from Southampton?"
- "Is a cruise to Venice worth it?"

Respond with JSON only:
{
  "suggested_prompts": ["Natural question 1?", "Natural question 2?", "Natural question 3?", "Natural question 4?", "Natural question 5?"],
  "primary_intent": "transactional|informational|navigational|commercial|comparison",
  "target_audience": "Brief description of who would search for this",
  "content_summary": "One sentence summary of what this page offers",
  "top_keywords": ["keyword1", "keyword2", "keyword3"]
}"""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this webpage and suggest NATURAL QUESTION-BASED search queries it could answer:

URL: {page_url}
Title: {page_title}
{meta_info}

Content excerpt:
{content_excerpt}

Generate suggested prompts as natural questions:"""
                    }
                ],
                temperature=0.4,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"LLM prompt suggestion for page: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Azure OpenAI prompt suggestion failed: {e}")
            return None


# Singleton instance
azure_openai_service = AzureOpenAIService()

