"""Project model for organizing prompts and pages."""

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Project(Base, UUIDMixin, TimestampMixin):
    """Project model - container for prompts, pages, and analysis."""
    
    __tablename__ = "projects"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Target domains to crawl (list of domain strings)
    target_domains = Column(JSONB, default=list)
    
    # Crawl configuration
    crawl_config = Column(JSONB, default=dict)
    # Example: {
    #   "max_pages": 100,
    #   "rate_limit": 1.0,
    #   "allowed_paths": ["/docs", "/support"],
    #   "excluded_paths": ["/admin"],
    #   "respect_robots": true
    # }
    
    # Human prompt examples for few-shot learning when generating candidate prompts
    example_prompts = Column(JSONB, default=list)
    # Example: [
    #   {"topic": "enclave", "prompt": "Is Buick Enclave a good car to buy?", "category": "branded"},
    #   {"topic": "suvs", "prompt": "What's the best mid-size SUV?", "category": "generic"},
    # ]
    
    # Owner user ID (optional for MVP)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    csv_imports = relationship("CSVImport", back_populates="project", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="project", cascade="all, delete-orphan")
    crawl_jobs = relationship("CrawlJob", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project {self.name}>"

