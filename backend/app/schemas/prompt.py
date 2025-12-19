"""Prompt Pydantic schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class PromptCreate(BaseModel):
    """Schema for creating a prompt (internal use)."""
    
    csv_import_id: UUID
    raw_text: str
    topic: Optional[str] = None
    region: Optional[str] = None
    popularity_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    visibility_score: Optional[float] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class CWVAssessment(BaseModel):
    """Schema for Core Web Vitals assessment."""
    
    status: str  # "passed", "failed", "unknown"
    performance_score: Optional[int] = None
    has_data: bool = False
    message: Optional[str] = None
    # Individual metric status
    lcp_ok: Optional[bool] = None
    inp_ok: Optional[bool] = None
    cls_ok: Optional[bool] = None


class PromptMatchInfo(BaseModel):
    """Schema for prompt match information."""
    
    page_id: UUID
    page_url: str
    page_title: Optional[str]
    similarity_score: float
    match_type: str
    matched_snippet: Optional[str]


class PromptResponse(BaseModel):
    """Schema for prompt response."""
    
    id: UUID
    raw_text: str
    normalized_text: Optional[str]
    topic: Optional[str]
    category: Optional[str]
    region: Optional[str]
    language: Optional[str]
    
    # Scores
    popularity_score: Optional[float]
    sentiment_score: Optional[float]
    visibility_score: Optional[float]
    
    # Intent
    intent_label: str
    transaction_score: float
    
    # Match status
    match_status: str
    best_match_score: Optional[float]
    
    # Extra data
    extra_data: Dict[str, Any]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Related data (optional)
    matches: Optional[List[PromptMatchInfo]] = None
    opportunity: Optional[Dict[str, Any]] = None
    cwv_assessment: Optional[CWVAssessment] = None
    
    class Config:
        from_attributes = True


class PromptListResponse(BaseModel):
    """Schema for listing prompts with pagination."""
    
    prompts: List[PromptResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PromptFilter(BaseModel):
    """Schema for filtering prompts."""
    
    topic: Optional[str] = None
    language: Optional[str] = None
    intent_label: Optional[str] = None
    match_status: Optional[str] = None
    min_transaction_score: Optional[float] = None
    max_transaction_score: Optional[float] = None
    min_popularity: Optional[float] = None
    search: Optional[str] = None

