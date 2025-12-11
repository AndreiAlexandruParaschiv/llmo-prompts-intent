"""Opportunity model for tracking content gaps and recommendations."""

from sqlalchemy import Column, String, Float, Text, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class OpportunityStatus(str, enum.Enum):
    """Status of opportunity in workflow."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class RecommendedAction(str, enum.Enum):
    """Recommended action types."""
    CREATE_FAQ = "create_faq"
    CREATE_ARTICLE = "create_article"
    CREATE_PRODUCT_PAGE = "create_product_page"
    CREATE_LANDING_PAGE = "create_landing_page"
    EXPAND_EXISTING = "expand_existing"
    ADD_CTA = "add_cta"
    ADD_STRUCTURED_DATA = "add_structured_data"
    TRANSLATE = "translate"
    CANONICALIZE = "canonicalize"
    OTHER = "other"


class Opportunity(Base, UUIDMixin, TimestampMixin):
    """Opportunity model - content gap with prioritized recommendation."""
    
    __tablename__ = "opportunities"
    
    prompt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One opportunity per prompt
    )
    
    # Priority scoring
    priority_score = Column(Float, nullable=False, default=0.0)
    # Formula: w1*popularity + w2*transaction_score + w3*|sentiment| - w4*difficulty
    
    # Component scores for transparency
    popularity_weight = Column(Float, nullable=True)
    transaction_weight = Column(Float, nullable=True)
    sentiment_weight = Column(Float, nullable=True)
    difficulty_weight = Column(Float, nullable=True)
    
    # Difficulty estimation (0-1, higher = harder)
    difficulty_score = Column(Float, nullable=True)
    difficulty_factors = Column(JSONB, default=dict)
    # Example: {
    #   "needs_new_page": true,
    #   "technical_complexity": 0.3,
    #   "content_complexity": 0.5,
    #   "translation_needed": false
    # }
    
    # Recommendation
    recommended_action = Column(
        Enum(RecommendedAction),
        default=RecommendedAction.OTHER,
        nullable=False,
    )
    
    # Reasoning for the recommendation
    reason = Column(Text, nullable=True)
    
    # Workflow status
    status = Column(
        Enum(OpportunityStatus),
        default=OpportunityStatus.NEW,
        nullable=False,
    )
    
    # Assigned user (for team features)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    
    # Notes and comments
    notes = Column(Text, nullable=True)
    
    # AI-generated content suggestion (Phase 3)
    content_suggestion = Column(JSONB, default=dict)
    # Example: {
    #   "outline": ["Introduction", "Key Points", "Conclusion"],
    #   "draft_content": "...",
    #   "keywords": ["shipping", "tracking"]
    # }
    
    # Related pages that could be expanded
    related_page_ids = Column(JSONB, default=list)
    
    # Relationships
    prompt = relationship("Prompt", back_populates="opportunity")
    
    # Indexes
    __table_args__ = (
        Index("ix_opportunities_status", "status"),
        Index("ix_opportunities_priority_score", "priority_score"),
        Index("ix_opportunities_recommended_action", "recommended_action"),
    )
    
    def __repr__(self):
        return f"<Opportunity {self.recommended_action} priority={self.priority_score:.2f}>"

