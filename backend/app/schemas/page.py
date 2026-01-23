"""Page Pydantic schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class PageCreate(BaseModel):
    """Schema for creating a page (internal use)."""
    
    project_id: UUID
    crawl_job_id: Optional[UUID] = None
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    content: Optional[str] = None


class MCPChecks(BaseModel):
    """Schema for MCP capability checks."""
    
    has_product_schema: bool = False
    has_price: bool = False
    has_add_to_cart: bool = False
    has_reviews: bool = False
    has_contact_form: bool = False
    has_cta: bool = False
    has_hreflang: List[str] = []
    has_canonical: bool = False
    page_speed_score: Optional[float] = None


class PageResponse(BaseModel):
    """Schema for page response."""
    
    id: UUID
    project_id: UUID
    url: str
    canonical_url: Optional[str]
    status_code: Optional[str]
    content_type: Optional[str]
    title: Optional[str]
    meta_description: Optional[str]
    word_count: Optional[str]
    structured_data: List[Dict[str, Any]]
    mcp_checks: Dict[str, Any]
    hreflang_tags: List[Dict[str, str]]
    crawled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PageListResponse(BaseModel):
    """Schema for listing pages."""
    
    pages: List[PageResponse]
    total: int
    page: int
    page_size: int


class CandidatePrompt(BaseModel):
    """Schema for a single candidate prompt."""
    
    text: str
    transaction_score: float
    intent: str
    funnel_stage: Optional[str] = None  # awareness, consideration, decision
    topic: Optional[str] = None
    sub_topic: Optional[str] = None
    audience_persona: Optional[str] = None
    reasoning: str
    target_audience: Optional[str] = None  # Legacy field, use audience_persona
    citation_trigger: Optional[str] = None


class CandidatePromptsResponse(BaseModel):
    """Schema for candidate prompts response."""
    
    page_id: UUID
    page_url: str
    page_title: Optional[str]
    page_topic: Optional[str] = None
    page_summary: Optional[str] = None
    prompts: List[CandidatePrompt]
    generated_at: Optional[str] = None
    cached: bool = False

