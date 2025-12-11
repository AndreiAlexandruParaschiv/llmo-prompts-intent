"""Intent classification service with comprehensive taxonomy."""

import re
from typing import Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class IntentType(str, Enum):
    """Comprehensive intent classification taxonomy."""
    TRANSACTIONAL = "transactional"           # User wants to buy/complete an action
    NAVIGATIONAL = "navigational"             # Go to a brand/service
    INFORMATIONAL = "informational"           # Learn something
    COMMERCIAL = "commercial"                 # Compare before buying (commercial investigation)
    EXPLORATORY = "exploratory"               # General topic browsing
    COMPARISON = "comparison"                 # Explicit decision-making between options
    TROUBLESHOOTING = "troubleshooting"       # Solve a problem
    OPINION_SEEKING = "opinion_seeking"       # User wants subjective answers
    EMOTIONAL = "emotional"                   # User expresses sentiment
    PROCEDURAL = "procedural"                 # Step-by-step actions / how-to
    REGULATORY = "regulatory"                 # Rules / policies / legal
    BRAND_MONITORING = "brand_monitoring"     # Off-site news/reviews about brand
    META = "meta"                             # Writing, generating, LLM tasks


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent: IntentType
    transaction_score: float  # 0-1, higher = more transactional
    confidence: float  # 0-1
    signals: List[str]  # Explanation of classification


# =============================================================================
# PATTERN DEFINITIONS FOR ALL INTENT TYPES
# =============================================================================

TRANSACTIONAL_PATTERNS = [
    # Purchase intent - "Book Virgin Atlantic flight"
    (r"\bbuy\b", 0.8),
    (r"\bpurchase\b", 0.8),
    (r"\border\b", 0.7),
    (r"\bbook\b", 0.7),
    (r"\breserve\b", 0.7),
    (r"\bsubscribe\b", 0.7),
    (r"\bsign\s*up\b", 0.6),
    (r"\bregister\b", 0.5),
    (r"\bdownload\b", 0.5),
    (r"\bget\s+started\b", 0.6),
    
    # Price/cost focused
    (r"\bprice\b", 0.5),
    (r"\bcost\b", 0.5),
    (r"\bhow\s+much\b", 0.5),
    (r"\bcheap(est)?\b", 0.6),
    (r"\bdiscount\b", 0.7),
    (r"\bdeal(s)?\b", 0.6),
    (r"\bpromo\s*code\b", 0.8),
    (r"\bcoupon\b", 0.8),
    (r"\bsale\b", 0.7),
    (r"\boffer(s)?\b", 0.5),
    
    # Sales events - high buying intent
    (r"\bblack\s*friday\b", 0.85),
    (r"\bcyber\s*monday\b", 0.85),
    (r"\bprime\s*day\b", 0.8),
    (r"\bholiday\s+sale\b", 0.8),
    (r"\bflash\s+sale\b", 0.8),
    (r"\bclearance\b", 0.7),
    (r"\blimited\s+(time\s+)?offer\b", 0.7),
    
    # Action-oriented
    (r"\bget\s+(a|the)?\s*quote\b", 0.7),
    (r"\bcalculat(e|or)\b", 0.5),
    (r"\badd\s+to\s+cart\b", 0.9),
    (r"\bcheckout\b", 0.9),
]

NAVIGATIONAL_PATTERNS = [
    # Brand/service navigation - "Virgin Atlantic manage my booking"
    (r"\bmanage\s+(my\s+)?booking\b", 0.9),
    (r"\bmy\s+account\b", 0.9),
    (r"\blogin\b", 0.9),
    (r"\blog\s*in\b", 0.9),
    (r"\bsign\s*in\b", 0.8),
    (r"\bwebsite\b", 0.6),
    (r"\bofficial\s+site\b", 0.8),
    (r"\bapp\b", 0.4),
    
    # Contact/support
    (r"\bcontact\b", 0.7),
    (r"\bcustomer\s+service\b", 0.8),
    (r"\bphone\s+number\b", 0.8),
    
    # Location
    (r"\bnear\s+me\b", 0.6),
    (r"\blocation\b", 0.5),
    (r"\bfind\s+(a|the)?\s*store\b", 0.7),
]

INFORMATIONAL_PATTERNS = [
    # Learning - "What is Virgin Atlantic's baggage policy?"
    (r"\bwhat\s+is\b", 0.7),
    (r"\bwhat\s+are\b", 0.7),
    (r"\bwhat\s+does\b", 0.7),
    (r"\bexplain\b", 0.8),
    (r"\bmeaning\b", 0.8),
    (r"\bdefinition\b", 0.9),
    (r"\blearn\s+about\b", 0.7),
    (r"\bunderstand\b", 0.6),
    (r"\bguide\b", 0.5),
    (r"\bfact[s]?\b", 0.5),
    (r"\bhistory\s+of\b", 0.6),
    (r"\boverview\b", 0.5),
]

COMMERCIAL_PATTERNS = [
    # Compare before buying - "Virgin Atlantic vs Lufthansa premium economy"
    (r"\bbest\b", 0.7),
    (r"\btop\s+\d+\b", 0.7),
    (r"\breview[s]?\b", 0.7),
    (r"\brating[s]?\b", 0.5),
    (r"\bcompar(e|ison)\b", 0.6),
    (r"\balternative[s]?\b", 0.6),
    (r"\brecommend(ed|ation)?\b", 0.6),
    (r"\bpros\s+and\s+cons\b", 0.7),
    (r"\bworth\s+it\b", 0.7),
    (r"\bshould\s+i\s+(buy|get|use|book)\b", 0.8),
]

COMPARISON_PATTERNS = [
    # Explicit decision-making - "Which is better: Virgin Atlantic or BA?"
    (r"\bvs\.?\b", 0.8),
    (r"\bversus\b", 0.8),
    (r"\bor\b.*\bwhich\b", 0.7),
    (r"\bwhich\s+is\s+better\b", 0.9),
    (r"\bwhich\s+one\b", 0.6),
    (r"\bcompare\s+.*\s+(to|with|and)\b", 0.8),
    (r"\bdifference\s+between\b", 0.7),
    (r"\b(.*)\s+or\s+(.*)\?", 0.6),  # X or Y?
]

EXPLORATORY_PATTERNS = [
    # General topic browsing - "Tell me about Virgin Atlantic lounges"
    (r"\btell\s+me\s+about\b", 0.8),
    (r"\bwhat\s+(can|do)\s+you\s+(tell|know)\b", 0.7),
    (r"\binterested\s+in\b", 0.5),
    (r"\bcurious\s+about\b", 0.6),
    (r"\bexplore\b", 0.6),
    (r"\bdiscover\b", 0.5),
    (r"\blearn\s+more\b", 0.6),
    (r"\bfind\s+out\b", 0.5),
    (r"\bshow\s+me\b", 0.5),
    (r"\bwhat\s+are\s+some\b", 0.6),
]

TROUBLESHOOTING_PATTERNS = [
    # Solve a problem - "Why is my e-ticket not working?"
    (r"\bnot\s+working\b", 0.9),
    (r"\bdoesn'?t\s+work\b", 0.9),
    (r"\bwon'?t\s+(load|open|start|work)\b", 0.8),
    (r"\berror\b", 0.8),
    (r"\bproblem\s+with\b", 0.7),
    (r"\bissue\s+with\b", 0.7),
    (r"\bfix\b", 0.6),
    (r"\bsolve\b", 0.6),
    (r"\btroubleshoot\b", 0.9),
    (r"\bcan'?t\s+(find|access|see|get|login|book)\b", 0.7),
    (r"\bfailed\b", 0.6),
    (r"\bwhy\s+(is|isn'?t|does|doesn'?t|can'?t|won'?t)\b", 0.6),
    (r"\bhelp\s+(me\s+)?with\b", 0.5),
]

OPINION_SEEKING_PATTERNS = [
    # Subjective answers - "Is Virgin Atlantic any good?"
    (r"\bany\s+good\b", 0.9),
    (r"\bworth\s+(it|the)\b", 0.8),
    (r"\bgood\s+choice\b", 0.7),
    (r"\bwhat\s+do\s+you\s+think\b", 0.9),
    (r"\bopinion\s+on\b", 0.9),
    (r"\byour\s+thoughts\b", 0.8),
    (r"\bhow\s+(good|bad)\s+is\b", 0.7),
    (r"\breliable\b", 0.5),
    (r"\btrustworthy\b", 0.6),
    (r"\breputable\b", 0.6),
    (r"\bdo\s+you\s+recommend\b", 0.8),
    (r"\bis\s+it\s+(safe|good|worth|legit)\b", 0.7),
]

EMOTIONAL_PATTERNS = [
    # Expresses sentiment - "The flight was awful"
    (r"\bawful\b", 0.8),
    (r"\bterrible\b", 0.8),
    (r"\bhorrible\b", 0.8),
    (r"\bamazing\b", 0.7),
    (r"\bfantastic\b", 0.7),
    (r"\bi\s+(love|hate|loved|hated)\b", 0.9),
    (r"\bworst\b", 0.8),
    (r"\bbest\s+experience\b", 0.7),
    (r"\bdisappoint(ed|ing)\b", 0.8),
    (r"\bfrustrat(ed|ing)\b", 0.8),
    (r"\bangry\b", 0.8),
    (r"\bhappy\s+with\b", 0.6),
    (r"\bnightmare\b", 0.9),
    (r"\bwonderful\b", 0.7),
    (r"\bexcited\b", 0.6),
]

PROCEDURAL_PATTERNS = [
    # Step-by-step actions - "How to upgrade my seat"
    (r"\bhow\s+to\b", 0.8),
    (r"\bhow\s+do\s+(i|you)\b", 0.8),
    (r"\bhow\s+can\s+i\b", 0.7),
    (r"\bstep[s]?\s+to\b", 0.9),
    (r"\bstep\s+by\s+step\b", 0.9),
    (r"\bprocess\s+(for|to|of)\b", 0.6),
    (r"\bprocedure\b", 0.7),
    (r"\btutorial\b", 0.6),
    (r"\binstructions\b", 0.7),
    (r"\bway\s+to\b", 0.5),
    (r"\b(upgrade|change|cancel|modify|update)\s+(my|a|the)\b", 0.7),
]

REGULATORY_PATTERNS = [
    # Rules / policies - "What is EU261?"
    (r"\bpolicy\b", 0.7),
    (r"\bpolicies\b", 0.7),
    (r"\brule[s]?\b", 0.7),
    (r"\bregulation[s]?\b", 0.8),
    (r"\blaw[s]?\b", 0.7),
    (r"\blegal\b", 0.6),
    (r"\brequirement[s]?\b", 0.6),
    (r"\brestriction[s]?\b", 0.6),
    (r"\bterms\s+(and|&)\s+conditions\b", 0.9),
    (r"\bterms\s+of\s+(service|use)\b", 0.8),
    (r"\bprivacy\s+policy\b", 0.8),
    (r"\brefund\s+policy\b", 0.8),
    (r"\ballowed\b", 0.5),
    (r"\bpermitted\b", 0.6),
    (r"\bprohibited\b", 0.7),
    (r"\beu\s*261\b", 0.9),
    (r"\bgdpr\b", 0.9),
    (r"\bcomplian(ce|t)\b", 0.7),
]

BRAND_MONITORING_PATTERNS = [
    # Off-site news/reviews - "What did the BBC say about Virgin Atlantic?"
    (r"\bwhat\s+(did|does|do)\s+.*\s+say\b", 0.8),
    (r"\bnews\s+about\b", 0.8),
    (r"\blatest\s+news\b", 0.8),
    (r"\barticle[s]?\s+about\b", 0.7),
    (r"\bmedia\s+coverage\b", 0.9),
    (r"\bpress\s+release\b", 0.8),
    (r"\bmentioned\s+in\b", 0.7),
    (r"\breported\b", 0.6),
    (r"\bcoverage\s+of\b", 0.7),
    (r"\bheadlines\b", 0.7),
    (r"\bwhat\s+.*\s+wrote\b", 0.7),
]

META_PATTERNS = [
    # Writing, generating, LLM tasks - "Write a review about Virgin Atlantic"
    (r"\bwrite\b", 0.8),
    (r"\bgenerate\b", 0.9),
    (r"\bcreate\b", 0.6),
    (r"\bcompose\b", 0.8),
    (r"\bdraft\b", 0.7),
    (r"\bsummarize\b", 0.8),
    (r"\bsummary\b", 0.7),
    (r"\btranslate\b", 0.8),
    (r"\brewrite\b", 0.9),
    (r"\bparaphrase\b", 0.9),
    (r"\blist\s+of\b", 0.5),
    (r"\bgive\s+me\s+(a|an)\b", 0.5),
    (r"\bformat\b", 0.6),
    (r"\bexamples?\s+of\b", 0.5),
]


class IntentClassifierService:
    """Comprehensive intent classification with 13 intent types."""
    
    def __init__(self):
        self.transactional_threshold = settings.TRANSACTIONAL_THRESHOLD
        self.openai_enabled = bool(settings.OPENAI_API_KEY)
    
    def classify(self, text: str) -> IntentResult:
        """
        Classify the intent using comprehensive taxonomy.
        
        Priority order (highest to lowest):
        1. Emotional (strong sentiment expression)
        2. Meta (LLM/writing tasks)
        3. Troubleshooting (problem-solving)
        4. Transactional (purchase intent)
        5. Comparison (explicit A vs B)
        6. Commercial (research before purchase)
        7. Navigational (go to specific page/service)
        8. Procedural (how-to steps)
        9. Regulatory (rules/policies)
        10. Brand Monitoring (news about brand)
        11. Opinion Seeking (subjective answers)
        12. Exploratory (general browsing)
        13. Informational (learning/facts - default)
        """
        if not text or not text.strip():
            return IntentResult(
                intent=IntentType.INFORMATIONAL,
                transaction_score=0.0,
                confidence=0.0,
                signals=["Empty text - defaulting to informational"]
            )
        
        text_lower = text.lower().strip()
        
        # Calculate scores for all intent types
        scores = {
            IntentType.TRANSACTIONAL: self._calculate_pattern_score(text_lower, TRANSACTIONAL_PATTERNS),
            IntentType.NAVIGATIONAL: self._calculate_pattern_score(text_lower, NAVIGATIONAL_PATTERNS),
            IntentType.INFORMATIONAL: self._calculate_pattern_score(text_lower, INFORMATIONAL_PATTERNS),
            IntentType.COMMERCIAL: self._calculate_pattern_score(text_lower, COMMERCIAL_PATTERNS),
            IntentType.COMPARISON: self._calculate_pattern_score(text_lower, COMPARISON_PATTERNS),
            IntentType.EXPLORATORY: self._calculate_pattern_score(text_lower, EXPLORATORY_PATTERNS),
            IntentType.TROUBLESHOOTING: self._calculate_pattern_score(text_lower, TROUBLESHOOTING_PATTERNS),
            IntentType.OPINION_SEEKING: self._calculate_pattern_score(text_lower, OPINION_SEEKING_PATTERNS),
            IntentType.EMOTIONAL: self._calculate_pattern_score(text_lower, EMOTIONAL_PATTERNS),
            IntentType.PROCEDURAL: self._calculate_pattern_score(text_lower, PROCEDURAL_PATTERNS),
            IntentType.REGULATORY: self._calculate_pattern_score(text_lower, REGULATORY_PATTERNS),
            IntentType.BRAND_MONITORING: self._calculate_pattern_score(text_lower, BRAND_MONITORING_PATTERNS),
            IntentType.META: self._calculate_pattern_score(text_lower, META_PATTERNS),
        }
        
        # Find highest scoring intent with priority ordering
        # Priority list (earlier = higher priority for tie-breaking)
        priority_order = [
            IntentType.EMOTIONAL,        # Strong sentiment takes priority
            IntentType.META,             # LLM tasks are clear
            IntentType.TROUBLESHOOTING,  # Problem-solving is distinct
            IntentType.TRANSACTIONAL,    # High business value
            IntentType.COMPARISON,       # Explicit comparison
            IntentType.COMMERCIAL,       # Research with purchase intent
            IntentType.NAVIGATIONAL,     # Going to specific place
            IntentType.PROCEDURAL,       # How-to steps
            IntentType.REGULATORY,       # Rules/policies
            IntentType.BRAND_MONITORING, # News/media
            IntentType.OPINION_SEEKING,  # Subjective questions
            IntentType.EXPLORATORY,      # General browsing
            IntentType.INFORMATIONAL,    # Catch-all for learning
        ]
        
        # Find best match
        best_intent = IntentType.INFORMATIONAL
        best_score = 0.0
        best_signals = []
        threshold = 0.25  # Minimum score to be considered
        
        for intent_type in priority_order:
            score, signals = scores[intent_type]
            if score >= threshold and score >= best_score:
                best_intent = intent_type
                best_score = score
                best_signals = signals
        
        # If no strong match, use fallback logic
        if best_score < threshold:
            best_intent, best_signals = self._apply_fallback_rules(text_lower)
            best_score = 0.3  # Moderate confidence for fallback
        
        # Calculate transaction score (0-1)
        trans_score = scores[IntentType.TRANSACTIONAL][0]
        comm_score = scores[IntentType.COMMERCIAL][0]
        comp_score = scores[IntentType.COMPARISON][0]
        
        if best_intent == IntentType.TRANSACTIONAL:
            transaction_score = min(1.0, 0.6 + trans_score)
        elif best_intent == IntentType.COMMERCIAL:
            transaction_score = min(0.8, 0.4 + comm_score)
        elif best_intent == IntentType.COMPARISON:
            transaction_score = min(0.7, 0.35 + comp_score)
        elif best_intent == IntentType.NAVIGATIONAL and trans_score > 0.2:
            transaction_score = min(0.5, 0.3 + trans_score)
        elif best_intent in [IntentType.OPINION_SEEKING, IntentType.EXPLORATORY]:
            transaction_score = min(0.4, 0.2 + comm_score)
        else:
            transaction_score = min(0.25, trans_score)
        
        # Calculate confidence
        confidence = min(1.0, best_score * 1.5)
        
        return IntentResult(
            intent=best_intent,
            transaction_score=transaction_score,
            confidence=confidence,
            signals=best_signals
        )
    
    def _apply_fallback_rules(self, text_lower: str) -> Tuple[IntentType, List[str]]:
        """Apply fallback rules when no pattern strongly matches."""
        
        # Check for question patterns
        if text_lower.endswith("?"):
            # Determine type of question
            if any(w in text_lower for w in ["how to", "how do i", "how can i", "steps to"]):
                return IntentType.PROCEDURAL, ["Question with 'how to' pattern"]
            elif any(w in text_lower for w in ["why is", "why isn't", "why does", "not working"]):
                return IntentType.TROUBLESHOOTING, ["Question about problem"]
            elif any(w in text_lower for w in ["policy", "rule", "allowed", "legal"]):
                return IntentType.REGULATORY, ["Question about rules/policy"]
            elif any(w in text_lower for w in ["good", "worth", "recommend", "opinion"]):
                return IntentType.OPINION_SEEKING, ["Subjective question detected"]
            elif any(w in text_lower for w in ["best", "vs", "versus", "compare", "better"]):
                return IntentType.COMMERCIAL, ["Comparison question"]
            elif any(w in text_lower for w in ["tell me about", "what are", "explain"]):
                return IntentType.EXPLORATORY, ["Exploratory question"]
            else:
                return IntentType.INFORMATIONAL, ["General question detected"]
        
        # Check for statement patterns
        first_word = text_lower.split()[0] if text_lower.split() else ""
        
        if first_word in ["write", "generate", "create", "compose", "draft", "summarize"]:
            return IntentType.META, ["Starts with generation verb"]
        elif first_word in ["how"]:
            return IntentType.PROCEDURAL, ["Starts with 'how'"]
        elif first_word in ["what", "where", "when", "who"]:
            return IntentType.INFORMATIONAL, ["Starts with question word"]
        elif first_word in ["why"]:
            return IntentType.TROUBLESHOOTING, ["Starts with 'why'"]
        elif first_word in ["which"]:
            return IntentType.COMPARISON, ["Starts with 'which'"]
        elif any(w in text_lower for w in ["book", "buy", "purchase", "order"]):
            return IntentType.TRANSACTIONAL, ["Contains transaction verb"]
        elif any(w in text_lower for w in ["login", "sign in", "my account"]):
            return IntentType.NAVIGATIONAL, ["Contains navigation term"]
        
        # Default to informational for any other query
        return IntentType.INFORMATIONAL, ["Default classification"]
    
    def _calculate_pattern_score(
        self, 
        text: str, 
        patterns: List[Tuple[str, float]]
    ) -> Tuple[float, List[str]]:
        """Calculate score based on pattern matches."""
        total_score = 0.0
        signals = []
        
        for pattern, weight in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                total_score += weight
                signals.append(f"Matched: {pattern}")
        
        # Normalize score (diminishing returns for multiple matches)
        normalized = min(1.0, total_score / 2) if total_score > 0 else 0.0
        
        return normalized, signals
    
    def _get_question_boost(self, text: str) -> float:
        """Get boost for question-like queries."""
        question_words = ["what", "how", "why", "when", "where", "who", "which", "is", "are", "can", "do", "does"]
        
        first_word = text.split()[0] if text.split() else ""
        
        if first_word in question_words or text.endswith("?"):
            return 0.2
        
        return 0.0
    
    def is_transactional(self, text: str) -> bool:
        """Quick check if query is transactional."""
        result = self.classify(text)
        return result.transaction_score >= self.transactional_threshold
    
    def get_transaction_score(self, text: str) -> float:
        """Get just the transaction score."""
        result = self.classify(text)
        return result.transaction_score
    
    def classify_with_llm(self, text: str) -> IntentResult:
        """
        Classify using Azure OpenAI for better accuracy.
        Falls back to rule-based if LLM unavailable.
        """
        from app.services.azure_openai import azure_openai_service
        
        # First, get rule-based classification
        rule_result = self.classify(text)
        
        # If LLM is not enabled, use rule-based
        if not settings.USE_LLM_FOR_INTENT or not azure_openai_service.enabled:
            return rule_result
        
        # Use LLM for better accuracy
        try:
            llm_result = azure_openai_service.classify_intent(text)
            
            if llm_result:
                intent_str = llm_result.get("intent", "informational").lower()
                
                # Map LLM response to our enum
                try:
                    intent_type = IntentType(intent_str)
                except ValueError:
                    # Handle case variations
                    intent_type = IntentType.INFORMATIONAL
                    for it in IntentType:
                        if it.value.lower() == intent_str.lower():
                            intent_type = it
                            break
                
                return IntentResult(
                    intent=intent_type,
                    transaction_score=llm_result.get("transaction_score", rule_result.transaction_score),
                    confidence=llm_result.get("confidence", 0.85),
                    signals=rule_result.signals + [f"AI: {llm_result.get('reasoning', 'AI classification')}"]
                )
        except Exception as e:
            logger.warning(f"LLM classification failed, using rule-based: {e}")
        
        return rule_result


# Singleton instance
intent_classifier = IntentClassifierService()

