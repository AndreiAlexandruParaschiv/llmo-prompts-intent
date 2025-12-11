"""Prompt model for storing and analyzing user queries."""

from sqlalchemy import Column, String, Float, Text, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin
from app.core.config import settings


class IntentLabel(str, enum.Enum):
    """Intent classification labels - comprehensive taxonomy."""
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


class MatchStatus(str, enum.Enum):
    """Status of content matching for this prompt."""
    PENDING = "pending"
    ANSWERED = "answered"
    PARTIAL = "partial"
    GAP = "gap"


class Prompt(Base, UUIDMixin, TimestampMixin):
    """Prompt model - stores user queries with NLP analysis."""
    
    __tablename__ = "prompts"
    
    csv_import_id = Column(
        UUID(as_uuid=True),
        ForeignKey("csv_imports.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Raw and normalized text
    raw_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=True)
    
    # Metadata from CSV
    topic = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True)
    
    # Detected language (ISO 639-1 code: en, fr, de, etc.)
    language = Column(String(10), nullable=True)
    
    # Scores (normalized 0-1)
    popularity_score = Column(Float, nullable=True)  # From CSV: Low=0.33, Medium=0.66, High=1.0
    sentiment_score = Column(Float, nullable=True)   # -1 to 1 scale
    visibility_score = Column(Float, nullable=True)  # From CSV percentage
    
    # Intent classification
    intent_label = Column(
        Enum(IntentLabel, values_callable=lambda x: [e.value for e in x]),
        default=IntentLabel.INFORMATIONAL,
        nullable=False,
    )
    transaction_score = Column(Float, default=0.0)  # 0-1, higher = more transactional
    
    # NLP embedding for semantic matching
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    
    # Match status
    match_status = Column(
        Enum(MatchStatus),
        default=MatchStatus.PENDING,
        nullable=False,
    )
    best_match_score = Column(Float, nullable=True)
    
    # Additional metadata from CSV
    extra_data = Column(JSONB, default=dict)
    # Stores: sources_urls, source_types, brand_mentions, position, etc.
    
    # Relationships
    csv_import = relationship("CSVImport", back_populates="prompts")
    matches = relationship("Match", back_populates="prompt", cascade="all, delete-orphan")
    opportunity = relationship("Opportunity", back_populates="prompt", uselist=False, cascade="all, delete-orphan")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_prompts_topic", "topic"),
        Index("ix_prompts_category", "category"),
        Index("ix_prompts_language", "language"),
        Index("ix_prompts_intent_label", "intent_label"),
        Index("ix_prompts_match_status", "match_status"),
        Index("ix_prompts_transaction_score", "transaction_score"),
    )
    
    def __repr__(self):
        return f"<Prompt {self.raw_text[:50]}...>"

