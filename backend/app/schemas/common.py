"""Common Pydantic schemas shared across modules."""

from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    class Config:
        from_attributes = True


class JobStatus(BaseModel):
    """Job status response."""
    
    job_id: str
    status: str
    ready: bool
    progress: Optional[dict] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class BaseResponseModel(BaseModel):
    """Base response model with common fields."""
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Simple message response."""
    
    message: str
    success: bool = True

