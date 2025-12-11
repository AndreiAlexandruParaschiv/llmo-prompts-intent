"""CSV upload and processing API endpoints."""

import os
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.models.csv_import import CSVImport, ImportStatus
from app.models.project import Project
from app.models.prompt import Prompt
from app.schemas.csv_import import (
    CSVPreviewResponse,
    CSVImportResponse,
    CSVProcessRequest,
    ColumnMapping,
)
from app.services.csv_parser import csv_parser

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload/{project_id}", response_model=CSVPreviewResponse)
async def upload_csv(
    project_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV file and get a preview with suggested column mappings.
    """
    # Verify project exists
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Save file
    file_path = csv_parser.save_uploaded_file(file.filename, content)
    
    # Get preview
    try:
        columns, preview_rows, total_rows = csv_parser.get_preview(file_path)
    except ValueError as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))
    
    # Suggest column mapping
    suggested_mapping = csv_parser.suggest_column_mapping(columns)
    
    # Create import record
    csv_import = CSVImport(
        id=uuid4(),
        project_id=project_id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        status=ImportStatus.PENDING,
        total_rows=total_rows,
    )
    db.add(csv_import)
    await db.commit()
    await db.refresh(csv_import)
    
    return CSVPreviewResponse(
        import_id=csv_import.id,
        filename=file.filename,
        columns=columns,
        preview_rows=preview_rows,
        total_rows=total_rows,
        suggested_mapping=ColumnMapping(**{k: v for k, v in suggested_mapping.items() if v}),
    )


@router.post("/{import_id}/process", response_model=dict)
async def process_csv(
    import_id: UUID,
    request: CSVProcessRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start processing a CSV import with the provided column mapping.
    """
    csv_import = await db.get(CSVImport, import_id)
    if not csv_import:
        raise HTTPException(status_code=404, detail="Import not found")
    
    if csv_import.status not in [ImportStatus.PENDING, ImportStatus.FAILED]:
        raise HTTPException(status_code=400, detail=f"Import is already {csv_import.status}")
    
    # Update mapping and status
    csv_import.column_mapping = request.column_mapping.model_dump(exclude_none=True)
    csv_import.status = ImportStatus.PROCESSING
    await db.commit()
    
    # Start Celery task
    from app.workers.csv_tasks import process_csv_import
    task = process_csv_import.delay(str(import_id))
    
    csv_import.job_id = task.id
    await db.commit()
    
    return {
        "import_id": str(import_id),
        "job_id": task.id,
        "status": "processing",
        "message": "CSV processing started"
    }


@router.get("/{import_id}", response_model=CSVImportResponse)
async def get_csv_import(
    import_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get CSV import status and details."""
    csv_import = await db.get(CSVImport, import_id)
    if not csv_import:
        raise HTTPException(status_code=404, detail="Import not found")
    
    return CSVImportResponse.model_validate(csv_import)


@router.get("/", response_model=dict)
async def list_csv_imports(
    project_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List CSV imports with optional filtering."""
    query = select(CSVImport)
    
    if project_id:
        query = query.where(CSVImport.project_id == project_id)
    if status:
        query = query.where(CSVImport.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Get page
    query = query.order_by(CSVImport.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    imports = result.scalars().all()
    
    return {
        "imports": [CSVImportResponse.model_validate(i) for i in imports],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/{import_id}")
async def delete_csv_import(
    import_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a CSV import and all associated prompts."""
    csv_import = await db.get(CSVImport, import_id)
    if not csv_import:
        raise HTTPException(status_code=404, detail="Import not found")
    
    # Delete file if exists
    if csv_import.file_path and os.path.exists(csv_import.file_path):
        os.remove(csv_import.file_path)
    
    await db.delete(csv_import)
    await db.commit()
    
    return {"message": "Import deleted successfully"}
