"""Crawled pages API endpoints."""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.page import Page
from app.models.match import Match
from app.models.crawl_job import CrawlJob, CrawlStatus
from app.schemas.page import PageResponse, PageListResponse
from app.services.azure_openai import azure_openai_service
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=PageListResponse)
async def list_pages(
    project_id: Optional[UUID] = Query(None),
    crawl_job_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    filter_type: Optional[str] = Query(None, description="Filter: successful, failed, with_jsonld, with_hreflang"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List crawled pages with filtering."""
    query = select(Page)
    
    if project_id:
        query = query.where(Page.project_id == project_id)
    
    if crawl_job_id:
        query = query.where(Page.crawl_job_id == crawl_job_id)
    
    if search:
        query = query.where(
            Page.url.ilike(f"%{search}%") |
            Page.title.ilike(f"%{search}%")
        )
    
    # Apply filter_type
    if filter_type == "successful":
        query = query.where(Page.status_code.like("2%"))
    elif filter_type == "failed":
        query = query.where(
            (Page.status_code.is_(None)) | 
            (~Page.status_code.like("2%"))
        )
    elif filter_type == "with_jsonld":
        query = query.where(func.jsonb_array_length(Page.structured_data) > 0)
    elif filter_type == "with_hreflang":
        query = query.where(func.jsonb_array_length(Page.hreflang_tags) > 0)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Get page
    query = query.order_by(Page.crawled_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    pages = result.scalars().all()
    
    return PageListResponse(
        pages=[
            PageResponse(
                id=p.id,
                project_id=p.project_id,
                url=p.url,
                canonical_url=p.canonical_url,
                status_code=p.status_code,
                content_type=p.content_type,
                title=p.title,
                meta_description=p.meta_description,
                word_count=p.word_count,
                structured_data=p.structured_data or [],
                mcp_checks=p.mcp_checks or {},
                hreflang_tags=p.hreflang_tags or [],
                crawled_at=p.crawled_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in pages
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=dict)
async def get_pages_stats(
    project_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated statistics for pages."""
    from sqlalchemy import case, and_
    
    query = select(Page)
    if project_id:
        query = query.where(Page.project_id == project_id)
    
    # Total count
    total_count = await db.scalar(
        select(func.count()).select_from(query.subquery())
    )
    
    # Build status query
    status_query = select(Page.status_code, func.count()).group_by(Page.status_code)
    if project_id:
        status_query = status_query.where(Page.project_id == project_id)
    status_result = await db.execute(status_query)
    status_counts = {row[0]: row[1] for row in status_result}
    
    # Count successful (2xx status)
    successful = sum(count for code, count in status_counts.items() if code and code.startswith('2'))
    
    # Count failed (non-2xx or null)
    failed = sum(count for code, count in status_counts.items() if not code or not code.startswith('2'))
    
    # Count pages with JSON-LD
    jsonld_query = select(func.count()).select_from(Page).where(
        func.jsonb_array_length(Page.structured_data) > 0
    )
    if project_id:
        jsonld_query = jsonld_query.where(Page.project_id == project_id)
    jsonld_count = await db.scalar(jsonld_query) or 0
    
    # Count pages with hreflang
    hreflang_query = select(func.count()).select_from(Page).where(
        func.jsonb_array_length(Page.hreflang_tags) > 0
    )
    if project_id:
        hreflang_query = hreflang_query.where(Page.project_id == project_id)
    hreflang_count = await db.scalar(hreflang_query) or 0
    
    return {
        "total": total_count or 0,
        "successful": successful,
        "failed": failed,
        "with_jsonld": jsonld_count,
        "with_hreflang": hreflang_count,
        "by_status_code": status_counts,
    }


@router.get("/crawl-jobs/list", response_model=dict)
async def list_crawl_jobs(
    project_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List crawl jobs."""
    query = select(CrawlJob)
    
    if project_id:
        query = query.where(CrawlJob.project_id == project_id)
    
    if status:
        query = query.where(CrawlJob.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Get page
    query = query.order_by(CrawlJob.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return {
        "crawl_jobs": [
            {
                "id": str(j.id),
                "project_id": str(j.project_id),
                "status": j.status.value if j.status else "pending",
                "total_urls": j.total_urls,
                "crawled_urls": j.crawled_urls,
                "failed_urls": j.failed_urls,
                "error_message": j.error_message,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.post("/crawl-jobs/{job_id}/cancel", response_model=dict)
async def cancel_crawl_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running crawl job."""
    crawl_job = await db.get(CrawlJob, job_id)
    if not crawl_job:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    
    if crawl_job.status not in [CrawlStatus.PENDING, CrawlStatus.RUNNING]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job with status: {crawl_job.status.value}"
        )
    
    # Update status to cancelled
    crawl_job.status = CrawlStatus.CANCELLED
    crawl_job.completed_at = datetime.utcnow()
    crawl_job.error_message = "Cancelled by user"
    await db.commit()
    
    # Try to revoke the Celery task if we have the task ID
    try:
        from app.core.celery_app import celery_app
        # The job might have an associated task
        celery_app.control.revoke(str(job_id), terminate=True)
    except Exception as e:
        logger.warning("Could not revoke Celery task", error=str(e))
    
    return {
        "status": "cancelled",
        "job_id": str(job_id),
        "message": "Crawl job cancelled successfully"
    }


@router.post("/generate-missing-embeddings", response_model=dict)
async def generate_missing_embeddings(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Generate embeddings for pages that are missing them."""
    from app.workers.nlp_tasks import generate_page_embeddings_batch
    
    # Get pages without embeddings
    query = select(Page.id).where(
        Page.project_id == project_id,
        Page.embedding.is_(None)
    )
    result = await db.execute(query)
    page_ids = [str(row[0]) for row in result.fetchall()]
    
    if not page_ids:
        return {"status": "no_pages", "message": "All pages already have embeddings"}
    
    # Process in batches
    batch_size = 50
    for i in range(0, len(page_ids), batch_size):
        batch = page_ids[i:i + batch_size]
        generate_page_embeddings_batch.delay(batch)
    
    return {
        "status": "processing",
        "pages_queued": len(page_ids),
        "message": f"Generating embeddings for {len(page_ids)} pages"
    }


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get page details."""
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return PageResponse(
        id=page.id,
        project_id=page.project_id,
        url=page.url,
        canonical_url=page.canonical_url,
        status_code=page.status_code,
        content_type=page.content_type,
        title=page.title,
        meta_description=page.meta_description,
        word_count=page.word_count,
        structured_data=page.structured_data or [],
        mcp_checks=page.mcp_checks or {},
        hreflang_tags=page.hreflang_tags or [],
        crawled_at=page.crawled_at,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


@router.get("/{page_id}/content", response_model=dict)
async def get_page_content(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get page full content."""
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {
        "id": str(page.id),
        "url": page.url,
        "title": page.title,
        "meta_description": page.meta_description,
        "content": page.content,
        "word_count": page.word_count,
    }


@router.delete("/{page_id}")
async def delete_page(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a page."""
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    await db.delete(page)
    await db.commit()
    
    return {"message": "Page deleted successfully"}


@router.post("/{project_id}/crawl-url", response_model=dict)
async def crawl_single_url(
    project_id: UUID,
    url: str,
    db: AsyncSession = Depends(get_db),
):
    """Crawl a single URL and add to project."""
    from app.models.project import Project
    from app.workers.crawler_tasks import crawl_single_url as crawl_task
    
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task = crawl_task.delay(str(project_id), url)
    
    return {
        "task_id": task.id,
        "url": url,
        "status": "started",
    }


@router.get("/orphan-pages", response_model=dict)
async def get_orphan_pages(
    project_id: UUID = Query(...),
    min_match_threshold: float = Query(0.5, description="Pages with best match below this are considered orphans"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_suggestions: bool = Query(False, description="Include AI-generated prompt suggestions"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pages that don't have good matches to any prompts (orphan pages).
    These are pages that exist but no user queries match them well.
    """
    from sqlalchemy import outerjoin
    from sqlalchemy.sql import literal_column
    
    # Subquery to get the best match score for each page
    best_match_subquery = (
        select(
            Match.page_id,
            func.max(Match.similarity_score).label("best_score")
        )
        .group_by(Match.page_id)
        .subquery()
    )
    
    # Query pages with their best match score (or NULL if no matches)
    query = (
        select(
            Page,
            best_match_subquery.c.best_score
        )
        .outerjoin(best_match_subquery, Page.id == best_match_subquery.c.page_id)
        .where(
            Page.project_id == project_id,
            Page.embedding.isnot(None),  # Only pages with embeddings
            or_(
                best_match_subquery.c.best_score.is_(None),  # No matches at all
                best_match_subquery.c.best_score < min_match_threshold  # Below threshold
            )
        )
    )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Get paginated results
    query = query.order_by(
        # Pages with NO matches first, then by lowest score
        best_match_subquery.c.best_score.asc().nullsfirst()
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    orphan_pages = []
    for row in rows:
        page_obj = row[0]
        best_score = row[1]
        
        page_data = {
            "id": str(page_obj.id),
            "url": page_obj.url,
            "title": page_obj.title,
            "meta_description": page_obj.meta_description,
            "word_count": page_obj.word_count,
            "best_match_score": round(best_score * 100, 1) if best_score else None,
            "match_status": "no_matches" if best_score is None else "low_match",
            "crawled_at": page_obj.crawled_at.isoformat() if page_obj.crawled_at else None,
        }
        
        # Include AI suggestions if requested
        if include_suggestions and azure_openai_service.enabled:
            suggestion = azure_openai_service.generate_prompt_suggestion(
                page_url=page_obj.url,
                page_title=page_obj.title or "",
                page_content=page_obj.content or "",
                meta_description=page_obj.meta_description
            )
            page_data["ai_suggestion"] = suggestion
        
        orphan_pages.append(page_data)
    
    return {
        "orphan_pages": orphan_pages,
        "total": total or 0,
        "page": page,
        "page_size": page_size,
        "min_match_threshold": min_match_threshold,
        "ai_enabled": azure_openai_service.enabled,
    }


@router.post("/orphan-pages/{page_id}/generate-suggestions", response_model=dict)
async def generate_orphan_page_suggestions(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate AI prompt suggestions for a specific orphan page."""
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    if not azure_openai_service.enabled:
        raise HTTPException(status_code=400, detail="AI service not available")
    
    suggestion = azure_openai_service.generate_prompt_suggestion(
        page_url=page.url,
        page_title=page.title or "",
        page_content=page.content or "",
        meta_description=page.meta_description
    )
    
    if not suggestion:
        raise HTTPException(status_code=500, detail="Failed to generate suggestions")
    
    return {
        "page_id": str(page_id),
        "url": page.url,
        "title": page.title,
        "suggestion": suggestion,
    }


@router.post("/{project_id}/import-urls", response_model=dict)
async def import_urls_bulk(
    project_id: UUID,
    urls: list[str],
    db: AsyncSession = Depends(get_db),
):
    """
    Import a list of URLs to crawl. 
    This is more efficient than full site crawling when you know which pages matter.
    """
    from uuid import uuid4
    from app.models.project import Project
    from app.models.crawl_job import CrawlJob, CrawlStatus
    from app.workers.crawler_tasks import crawl_url_list
    
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    # Normalize URLs
    normalized_urls = []
    for url in urls:
        url = url.strip()
        if url and not url.startswith('#'):  # Skip empty and comment lines
            # Add https if no protocol
            if not url.startswith('http://') and not url.startswith('https://'):
                url = f"https://{url}"
            normalized_urls.append(url)
    
    if not normalized_urls:
        raise HTTPException(status_code=400, detail="No valid URLs found")
    
    # Create crawl job
    crawl_job = CrawlJob(
        id=uuid4(),
        project_id=project_id,
        status=CrawlStatus.PENDING,
        total_urls=len(normalized_urls),
        config={
            "urls": normalized_urls,
            "mode": "url_list",
        },
    )
    db.add(crawl_job)
    await db.commit()
    
    # Start Celery task
    task = crawl_url_list.delay(str(crawl_job.id), normalized_urls)
    
    crawl_job.celery_task_id = task.id
    await db.commit()
    
    return {
        "crawl_job_id": str(crawl_job.id),
        "task_id": task.id,
        "url_count": len(normalized_urls),
        "status": "started",
    }
