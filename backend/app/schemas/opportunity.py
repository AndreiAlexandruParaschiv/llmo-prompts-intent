"""Opportunity Pydantic schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class DifficultyFactors(BaseModel):
    """Schema for difficulty estimation factors."""
    
    needs_new_page: bool = False
    technical_complexity: float = Field(default=0.0, ge=0.0, le=1.0)
    content_complexity: float = Field(default=0.0, ge=0.0, le=1.0)
    translation_needed: bool = False
    estimated_word_count: Optional[int] = None


class ContentSuggestion(BaseModel):
    """Schema for AI-generated content suggestions."""
    
    outline: List[str] = Field(default_factory=list)
    draft_content: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    target_word_count: Optional[int] = None


class OpportunityCreate(BaseModel):
    """Schema for creating an opportunity (internal use)."""
    
    prompt_id: UUID
    priority_score: float
    recommended_action: str
    reason: Optional[str] = None
    difficulty_score: Optional[float] = None
    difficulty_factors: Optional[DifficultyFactors] = None


class OpportunityUpdate(BaseModel):
    """Schema for updating an opportunity."""
    
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None


class OpportunityResponse(BaseModel):
    """Schema for opportunity response."""
    
    id: UUID
    prompt_id: UUID
    priority_score: float
    difficulty_score: Optional[float]
    difficulty_factors: Dict[str, Any]
    recommended_action: str
    reason: Optional[str]
    status: str
    assigned_to: Optional[UUID]
    notes: Optional[str]
    content_suggestion: Dict[str, Any]
    related_page_ids: List[UUID]
    created_at: datetime
    updated_at: datetime
    
    # Related prompt data (for display)
    prompt_text: Optional[str] = None
    prompt_topic: Optional[str] = None
    prompt_intent: Optional[str] = None
    prompt_transaction_score: Optional[float] = None
    prompt_popularity_score: Optional[float] = None
    prompt_sentiment_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    """Schema for listing opportunities."""
    
    opportunities: List[OpportunityResponse]
    total: int
    page: int
    page_size: int
    
    # Summary statistics
    by_status: Dict[str, int] = Field(default_factory=dict)
    by_action: Dict[str, int] = Field(default_factory=dict)


class OpportunityFilter(BaseModel):
    """Schema for filtering opportunities."""
    
    status: Optional[str] = None
    recommended_action: Optional[str] = None
    min_priority: Optional[float] = None
    max_difficulty: Optional[float] = None
    assigned_to: Optional[UUID] = None

