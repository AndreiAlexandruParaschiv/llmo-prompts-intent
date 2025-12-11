"""Project Pydantic schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class CrawlConfig(BaseModel):
    """Crawl configuration schema."""
    
    max_pages: int = Field(default=100, ge=1, le=10000)
    rate_limit: float = Field(default=1.0, ge=0.1, le=10.0)
    allowed_paths: List[str] = Field(default_factory=list)
    excluded_paths: List[str] = Field(default_factory=list)
    respect_robots: bool = True
    timeout: int = Field(default=30000, ge=5000, le=120000)
    render_js: bool = True


class ProjectCreate(BaseModel):
    """Schema for creating a project."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_domains: List[str] = Field(default_factory=list)
    crawl_config: Optional[CrawlConfig] = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_domains: Optional[List[str]] = None
    crawl_config: Optional[CrawlConfig] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""
    
    id: UUID
    name: str
    description: Optional[str]
    target_domains: List[str]
    crawl_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    prompt_count: int = 0
    page_count: int = 0
    opportunity_count: int = 0
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for listing projects."""
    
    projects: List[ProjectResponse]
    total: int

