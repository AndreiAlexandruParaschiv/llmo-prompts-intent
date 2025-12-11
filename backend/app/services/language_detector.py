"""Language detection service."""

from typing import Optional, Tuple
from langdetect import detect, detect_langs, LangDetectException
from langdetect.detector_factory import init_factory

from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize langdetect
try:
    init_factory()
except:
    pass  # Already initialized


# Language code mapping
LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French", 
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "ja": "Japanese",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ko": "Korean",
    "ar": "Arabic",
}


class LanguageDetectorService:
    """Service for detecting language of text."""
    
    def __init__(self):
        self.supported_languages = {"en", "fr", "de", "es", "it", "pt", "nl", "pl", "ru", "ja", "zh-cn", "zh-tw", "ko", "ar"}
        self.default_language = "en"
    
    def detect(self, text: str) -> Tuple[str, float]:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or len(text.strip()) < 3:
            return self.default_language, 0.0
        
        try:
            # Get language probabilities
            langs = detect_langs(text)
            
            if langs:
                top_lang = langs[0]
                lang_code = top_lang.lang
                confidence = top_lang.prob
                
                # Normalize language codes
                lang_code = self._normalize_lang_code(lang_code)
                
                return lang_code, confidence
            
            return self.default_language, 0.0
            
        except LangDetectException as e:
            logger.warning("Language detection failed", error=str(e), text=text[:100])
            return self.default_language, 0.0
    
    def detect_simple(self, text: str) -> str:
        """Simple detection returning just the language code."""
        lang, _ = self.detect(text)
        return lang
    
    def _normalize_lang_code(self, code: str) -> str:
        """Normalize language code to standard form."""
        # Handle Chinese variants
        if code == "zh-cn" or code == "zh":
            return "zh-cn"
        if code == "zh-tw":
            return "zh-tw"
        
        # Return first part of hyphenated codes
        return code.split("-")[0].lower()
    
    def get_language_name(self, code: str) -> str:
        """Get human-readable language name."""
        return LANGUAGE_NAMES.get(code, code.upper())
    
    def group_by_language(self, code: str) -> str:
        """
        Map language code to region group.
        
        Returns:
            One of: ENG, FR, DE, OTHER
        """
        if code == "en":
            return "ENG"
        elif code == "fr":
            return "FR"
        elif code == "de":
            return "DE"
        else:
            return "OTHER"


# Singleton instance
language_detector = LanguageDetectorService()

