"""CSV Import Pydantic schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class ColumnMapping(BaseModel):
    """Schema for CSV column mapping."""
    
    prompt: str = Field(..., description="Column name for prompt text")
    topic: Optional[str] = Field(None, description="Column name for topic")
    region: Optional[str] = Field(None, description="Column name for region")
    popularity: Optional[str] = Field(None, description="Column name for popularity")
    sentiment: Optional[str] = Field(None, description="Column name for sentiment")
    visibility_score: Optional[str] = Field(None, description="Column name for visibility score")
    sources_urls: Optional[str] = Field(None, description="Column name for source URLs")
    source_types: Optional[str] = Field(None, description="Column name for source types")


class CSVImportCreate(BaseModel):
    """Schema for creating a CSV import (after upload)."""
    
    project_id: UUID
    column_mapping: ColumnMapping


class CSVPreviewRow(BaseModel):
    """Schema for a preview row."""
    
    row_number: int
    data: Dict[str, Any]


class CSVPreviewResponse(BaseModel):
    """Schema for CSV preview response."""
    
    import_id: UUID
    filename: str
    columns: List[str]
    preview_rows: List[CSVPreviewRow]
    total_rows: int
    suggested_mapping: Optional[ColumnMapping] = None


class CSVImportResponse(BaseModel):
    """Schema for CSV import response."""
    
    id: UUID
    project_id: UUID
    filename: str
    status: str
    total_rows: Optional[int]
    processed_rows: int
    failed_rows: int
    error_message: Optional[str]
    column_mapping: Dict[str, str]
    job_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CSVProcessRequest(BaseModel):
    """Schema for processing a CSV import."""
    
    column_mapping: ColumnMapping

