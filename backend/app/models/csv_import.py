"""CSV Import model for tracking uploaded files."""

from sqlalchemy import Column, String, Integer, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class ImportStatus(str, enum.Enum):
    """Status of CSV import processing."""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CSVImport(Base, UUIDMixin, TimestampMixin):
    """CSV Import model - tracks uploaded CSV files and processing status."""
    
    __tablename__ = "csv_imports"
    
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # Processing status
    status = Column(
        Enum(ImportStatus),
        default=ImportStatus.PENDING,
        nullable=False,
    )
    error_message = Column(String(1024), nullable=True)
    
    # Column mapping configuration
    column_mapping = Column(JSONB, default=dict)
    # Example: {
    #   "prompt": "Prompt",
    #   "topic": "Topic",
    #   "popularity": "Popularity",
    #   "sentiment": "Sentiment",
    #   "region": "Region"
    # }
    
    # Processing statistics
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    # Celery job ID for tracking
    job_id = Column(String(255), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="csv_imports")
    prompts = relationship("Prompt", back_populates="csv_import", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CSVImport {self.filename} ({self.status})>"

