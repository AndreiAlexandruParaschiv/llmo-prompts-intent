"""Match model for storing prompt-to-page semantic matches."""

from sqlalchemy import Column, String, Float, Text, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class MatchType(str, enum.Enum):
    """Type of match found."""
    EXACT = "exact"       # Exact keyword/phrase match
    SEMANTIC = "semantic"  # Embedding similarity match
    PARTIAL = "partial"    # Partial keyword match


class Match(Base, UUIDMixin, TimestampMixin):
    """Match model - links prompts to matching pages with similarity scores."""
    
    __tablename__ = "matches"
    
    prompt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    page_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Similarity score (0-1, cosine similarity)
    similarity_score = Column(Float, nullable=False)
    
    # Type of match
    match_type = Column(
        Enum(MatchType),
        default=MatchType.SEMANTIC,
        nullable=False,
    )
    
    # Matched text snippet from the page
    matched_snippet = Column(Text, nullable=True)
    
    # Rank among all matches for this prompt (1 = best match)
    rank = Column(String(10), nullable=True)
    
    # Relationships
    prompt = relationship("Prompt", back_populates="matches")
    page = relationship("Page", back_populates="matches")
    
    # Indexes
    __table_args__ = (
        Index("ix_matches_prompt_id", "prompt_id"),
        Index("ix_matches_page_id", "page_id"),
        Index("ix_matches_similarity_score", "similarity_score"),
    )
    
    def __repr__(self):
        return f"<Match prompt={self.prompt_id} page={self.page_id} score={self.similarity_score:.2f}>"

