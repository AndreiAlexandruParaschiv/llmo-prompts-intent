"""Page model for storing crawled website content."""

from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, UUIDMixin, TimestampMixin
from app.core.config import settings


class Page(Base, UUIDMixin, TimestampMixin):
    """Page model - stores crawled website pages with content and metadata."""
    
    __tablename__ = "pages"
    
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    crawl_job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # URL information
    url = Column(String(2048), nullable=False)
    canonical_url = Column(String(2048), nullable=True)
    
    # HTTP response info
    status_code = Column(String(10), nullable=True)
    content_type = Column(String(100), nullable=True)
    
    # Page content
    title = Column(String(512), nullable=True)
    meta_description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # Extracted visible text
    
    # Word count for difficulty estimation
    word_count = Column(String(20), nullable=True)
    
    # Path to HTML snapshot file
    html_snapshot_path = Column(String(512), nullable=True)
    
    # Structured data (JSON-LD, microdata)
    structured_data = Column(JSONB, default=list)
    # Example: [{"@type": "Product", "name": "...", "price": "..."}]
    
    # MCP capability checks
    mcp_checks = Column(JSONB, default=dict)
    # Example: {
    #   "has_product_schema": true,
    #   "has_price": true,
    #   "has_add_to_cart": false,
    #   "has_reviews": true,
    #   "has_contact_form": false,
    #   "has_cta": true,
    #   "has_hreflang": ["en", "fr", "de"],
    #   "has_canonical": true
    # }
    
    # SEO metadata
    hreflang_tags = Column(JSONB, default=list)  # List of {lang, url}
    
    # NLP embedding for semantic matching
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    
    # Crawl timestamp
    crawled_at = Column(DateTime, nullable=True)
    
    # Core Web Vitals (cached from PageSpeed Insights)
    cwv_data = Column(JSONB, nullable=True)  # Stores CWV metrics
    # Example: {
    #   "lcp": 2500, "lcp_score": "good",
    #   "cls": 0.1, "cls_score": "good",
    #   "inp": 200, "inp_score": "good",
    #   "performance_score": 85,
    #   "fetched_at": "2024-01-15T10:30:00Z"
    # }
    
    # Candidate prompts (AI-generated queries that would lead LLMs to cite this page)
    candidate_prompts = Column(JSONB, nullable=True)
    # Example: {
    #   "prompts": [
    #     {"text": "...", "transaction_score": 0.85, "intent": "commercial", ...}
    #   ],
    #   "generated_at": "2024-01-15T10:30:00Z"
    # }
    
    # Relationships
    project = relationship("Project", back_populates="pages")
    crawl_job = relationship("CrawlJob", back_populates="pages")
    matches = relationship("Match", back_populates="page", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_pages_url", "url"),
        Index("ix_pages_project_id", "project_id"),
    )
    
    def __repr__(self):
        return f"<Page {self.url[:50]}...>"

