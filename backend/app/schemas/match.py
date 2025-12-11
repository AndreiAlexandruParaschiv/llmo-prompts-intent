"""Match Pydantic schemas."""

from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class MatchResponse(BaseModel):
    """Schema for match response."""
    
    id: UUID
    prompt_id: UUID
    page_id: UUID
    similarity_score: float
    match_type: str
    matched_snippet: Optional[str]
    rank: Optional[str]
    created_at: datetime
    
    # Related data
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    
    class Config:
        from_attributes = True

