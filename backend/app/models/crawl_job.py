"""CrawlJob model for tracking website crawling jobs."""

from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class CrawlStatus(str, enum.Enum):
    """Status of crawl job."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlJob(Base, UUIDMixin, TimestampMixin):
    """CrawlJob model - tracks website crawling operations."""
    
    __tablename__ = "crawl_jobs"
    
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Job status
    status = Column(
        Enum(CrawlStatus),
        default=CrawlStatus.PENDING,
        nullable=False,
    )
    
    # Crawl configuration (snapshot at job creation)
    config = Column(JSONB, default=dict)
    # Includes: start_urls, max_pages, rate_limit, etc.
    
    # Progress tracking
    total_urls = Column(Integer, default=0)
    crawled_urls = Column(Integer, default=0)
    failed_urls = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(String(1024), nullable=True)
    errors = Column(JSONB, default=list)  # List of {url, error, timestamp}
    
    # Celery job ID
    celery_task_id = Column(String(255), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="crawl_jobs")
    pages = relationship("Page", back_populates="crawl_job")
    
    def __repr__(self):
        return f"<CrawlJob {self.id} ({self.status})>"

