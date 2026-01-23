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


    def generate_candidate_prompts(
        self,
        page_url: str,
        page_title: str,
        page_content: str,
        meta_description: Optional[str] = None,
        seo_data: Optional[Dict[str, Any]] = None,
        example_prompts: Optional[List[Dict[str, str]]] = None,
        num_prompts: int = 8
    ) -> Optional[Dict[str, Any]]:
        """
        Generate high-impact candidate prompts that would make LLMs cite this page.
        
        Generates TWO types of prompts:
        1. GENERIC prompts (for citation tracking) - category-level queries without brand names
        2. BRANDED prompts (for verification/sentiment) - brand-specific queries
        
        Args:
            seo_data: Optional SEO data with top keywords, traffic, etc.
                      e.g. {"top_keyword": "buick enclave", "keyword_volume": 138000, "traffic": 42212}
            example_prompts: Optional list of human-provided prompt examples for few-shot learning
                      e.g. [{"prompt": "Is Buick Enclave a good car?", "category": "branded"}, ...]
        
        Returns dict with:
        - prompts: List of candidate prompts with transaction scores, categories, and reasoning
        - page_topic: Overall topic of the page
        - page_summary: Brief summary of what the page offers
        - brand_name: Detected brand name from the page
        - generated_at: Timestamp of generation
        """
        if not self.enabled or not self.client:
            return None
        
        content_excerpt = page_content[:2500] if page_content else ""
        meta_info = f"\nMeta Description: {meta_description}" if meta_description else ""
        
        # Build SEO context if available
        seo_context = ""
        if seo_data:
            top_kw = seo_data.get('top_keyword', '')
            kw_vol = seo_data.get('keyword_volume', 0)
            traffic = seo_data.get('traffic', 0)
            if top_kw:
                seo_context = f"\n\nSEO DATA (from search analytics):\n"
                seo_context += f"- Top keyword driving traffic: \"{top_kw}\""
                if kw_vol:
                    seo_context += f" (monthly searches: {kw_vol:,})"
                seo_context += "\n"
                if traffic:
                    seo_context += f"- Current organic traffic: {traffic:,} visits/month\n"
                seo_context += "\nIMPORTANT: Use this keyword data to generate more relevant prompts that match real user search behavior."
        
        # Build examples context if available (only use human-provided examples)
        examples_context = ""
        if example_prompts and len(example_prompts) > 0:
            # Filter to only human-provided examples
            human_examples = [p for p in example_prompts if p.get('origin') == 'human']
            
            if human_examples:
                # Separate into branded and generic examples
                generic_examples = [p for p in human_examples if p.get('category') == 'generic'][:5]
                branded_examples = [p for p in human_examples if p.get('category') == 'branded'][:5]
                
                examples_context = "\n\nREAL HUMAN PROMPT EXAMPLES (use these as inspiration for tone and style):\n"
                
                if generic_examples:
                    examples_context += "\nGENERIC prompts (no brand name):\n"
                    for ex in generic_examples:
                        examples_context += f'- "{ex.get("prompt", "")}"\n'
                
                if branded_examples:
                    examples_context += "\nBRANDED prompts (with brand name):\n"
                    for ex in branded_examples:
                        examples_context += f'- "{ex.get("prompt", "")}"\n'
                
                examples_context += "\nIMPORTANT: Generate prompts that match the natural, conversational style of these human examples."
        
        try:
            response = self.client.chat.completions.create(
                model=settings.AZURE_COMPLETION_DEPLOYMENT,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert at understanding how real humans ask questions to AI assistants like ChatGPT, Claude, Perplexity, and Google's AI Overview.

Your task: Generate {num_prompts} HIGH-IMPACT prompts/questions for LLMO (LLM Optimization). 

CRITICAL: Generate TWO CATEGORIES of prompts:

## CATEGORY 1: GENERIC PROMPTS (4-5 prompts)
These are for CITATION TRACKING - queries where the brand wants to BE MENTIONED/CITED.
- DO NOT include the brand name in these prompts
- Use category/industry-level queries
- These test whether the LLM will cite this brand when answering general questions

GENERIC EXAMPLES:
- "what's the best luxury suv for a family of 6?"
- "which electric car has the longest range under 60k?"
- "what's the best full-size suv for towing a boat?"
- "what car brands let you order online and deliver to your home?"
- "what's the most reliable luxury sedan for 2025?"

## CATEGORY 2: BRANDED PROMPTS (3-4 prompts)
These are for VERIFICATION and SENTIMENT TRACKING - queries about the specific brand.
- Include the brand/product name
- Test if LLM has correct information (verification)
- Test sentiment/perception of the brand (sentiment)
- Include comparison prompts with competitors

BRANDED EXAMPLES:
- "is the cadillac escalade worth the price?"
- "how does the lyriq compare to tesla model y?"
- "what's the towing capacity of the 2025 escalade?"
- "are cadillac suvs reliable?"

PROMPT CHARACTERISTICS:
1. CASUAL TONE: Use lowercase, contractions, informal phrasing (how real people type)
2. REAL INTENT: Focus on what people ACTUALLY want to know
3. ACTIONABLE: Prompts that marketers can track and act on
4. QUESTION FORMAT: ALL prompts MUST end with a question mark (?) - these are questions people ask LLMs

PROMPT CATEGORIES (prompt_category field):
- "generic" - No brand name, category-level query (for citation tracking)
- "comparison" - Compares this brand vs competitors (competitive positioning)
- "branded_verify" - Brand-specific factual/specs question (accuracy verification)
- "branded_sentiment" - Brand perception/opinion question (sentiment tracking)

Respond with JSON only:
{{
  "page_topic": "Main topic/category (e.g., 'Luxury SUVs', 'Electric Vehicles')",
  "page_summary": "One sentence summary of what this page offers",
  "brand_name": "The brand name detected from this page",
  "product_category": "The product category (e.g., 'SUV', 'Sedan', 'Electric Car')",
  "prompts": [
    {{
      "text": "The casual, natural question",
      "prompt_category": "generic|comparison|branded_verify|branded_sentiment",
      "transaction_score": 0.0-1.0,
      "intent": "transactional|commercial|comparison|informational",
      "funnel_stage": "awareness|consideration|decision",
      "topic": "Specific topic this prompt relates to",
      "sub_topic": "More specific sub-topic if applicable",
      "audience_persona": "Type of person asking",
      "reasoning": "Why this prompt is valuable for tracking",
      "citation_trigger": "What content would be cited OR what we're verifying"
    }}
  ]
}}

IMPORTANT: Ensure a good mix - approximately 50-60% generic prompts and 40-50% branded prompts."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this webpage and generate {num_prompts} prompts - both GENERIC (for citation tracking) and BRANDED (for verification/sentiment):

URL: {page_url}
Title: {page_title}
{meta_info}{seo_context}{examples_context}

Content excerpt:
{content_excerpt}

Generate a mix of:
- GENERIC prompts (no brand name) for citation tracking
- BRANDED prompts for verification and sentiment tracking

Make them sound like how real people ACTUALLY talk to AI assistants:"""
                    }
                ],
                temperature=0.6,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Add generation timestamp and page info
            from datetime import datetime
            result["generated_at"] = datetime.utcnow().isoformat()
            result["page_url"] = page_url
            result["page_title"] = page_title
            
            logger.debug(f"LLM candidate prompts for page: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Azure OpenAI candidate prompts generation failed: {e}")
            return None


# Singleton instance
azure_openai_service = AzureOpenAIService()

