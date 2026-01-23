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
from app.schemas.page import PageResponse, PageListResponse, CandidatePromptsResponse, CandidatePrompt
from app.services.azure_openai import azure_openai_service
from datetime import datetime
from fastapi.responses import StreamingResponse
import csv
import io

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


@router.get("/candidate-prompts/list")
async def list_all_candidate_prompts(
    project_id: UUID = Query(..., description="Project ID"),
    intent: Optional[str] = Query(None, description="Filter by intent"),
    funnel_stage: Optional[str] = Query(None, description="Filter by funnel stage"),
    search: Optional[str] = Query(None, description="Search in prompt text"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    List all candidate prompts for a project with filtering and pagination.
    Returns prompts from all pages that have candidate_prompts generated.
    """
    # Get all pages with candidate prompts for this project
    query = select(Page).where(
        Page.project_id == project_id,
        Page.candidate_prompts.isnot(None)
    )
    
    result = await db.execute(query)
    pages = result.scalars().all()
    
    # Flatten all prompts with their page info
    all_prompts = []
    for page_obj in pages:
        cached_data = page_obj.candidate_prompts
        page_topic = cached_data.get('page_topic', '')
        page_summary = cached_data.get('page_summary', '')
        generated_at = cached_data.get('generated_at', '')
        
        for prompt in cached_data.get('prompts', []):
            prompt_data = {
                'page_id': str(page_obj.id),
                'page_url': page_obj.url,
                'page_title': page_obj.title,
                'page_topic': page_topic,
                'page_summary': page_summary,
                'text': prompt.get('text', ''),
                'intent': prompt.get('intent', ''),
                'funnel_stage': prompt.get('funnel_stage', ''),
                'topic': prompt.get('topic', ''),
                'sub_topic': prompt.get('sub_topic', ''),
                'audience_persona': prompt.get('audience_persona', prompt.get('target_audience', '')),
                'transaction_score': prompt.get('transaction_score', 0),
                'citation_trigger': prompt.get('citation_trigger', ''),
                'reasoning': prompt.get('reasoning', ''),
                'generated_at': generated_at,
            }
            
            # Apply filters
            if intent and prompt_data['intent'] != intent:
                continue
            if funnel_stage and prompt_data['funnel_stage'] != funnel_stage:
                continue
            if search and search.lower() not in prompt_data['text'].lower():
                continue
            
            all_prompts.append(prompt_data)
    
    # Sort by transaction score (highest first)
    all_prompts.sort(key=lambda x: x['transaction_score'], reverse=True)
    
    # Pagination
    total = len(all_prompts)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_prompts = all_prompts[start:end]
    
    # Compute stats
    stats = {
        'total_prompts': total,
        'by_intent': {},
        'by_funnel_stage': {},
        'by_audience': {},
    }
    
    for p in all_prompts:
        intent_val = p['intent'] or 'unknown'
        funnel_val = p['funnel_stage'] or 'unknown'
        audience_val = p['audience_persona'] or 'unknown'
        
        stats['by_intent'][intent_val] = stats['by_intent'].get(intent_val, 0) + 1
        stats['by_funnel_stage'][funnel_val] = stats['by_funnel_stage'].get(funnel_val, 0) + 1
        stats['by_audience'][audience_val] = stats['by_audience'].get(audience_val, 0) + 1
    
    return {
        'prompts': paginated_prompts,
        'total': total,
        'page': page,
        'page_size': page_size,
        'stats': stats,
    }


@router.get("/candidate-prompts/stats")
async def get_candidate_prompts_stats(
    project_id: UUID = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics about candidate prompts generation status for a project.
    """
    # Count total pages
    total_pages_query = select(func.count()).select_from(Page).where(Page.project_id == project_id)
    total_pages = await db.scalar(total_pages_query) or 0
    
    # Count pages with candidate prompts
    pages_with_prompts_query = select(func.count()).select_from(Page).where(
        Page.project_id == project_id,
        Page.candidate_prompts.isnot(None)
    )
    pages_with_prompts = await db.scalar(pages_with_prompts_query) or 0
    
    # Count total prompts
    query = select(Page.candidate_prompts).where(
        Page.project_id == project_id,
        Page.candidate_prompts.isnot(None)
    )
    result = await db.execute(query)
    total_prompts = 0
    by_intent = {}
    by_funnel_stage = {}
    
    for row in result:
        if row[0] and 'prompts' in row[0]:
            for p in row[0]['prompts']:
                total_prompts += 1
                intent = p.get('intent', 'unknown')
                funnel = p.get('funnel_stage', 'unknown')
                by_intent[intent] = by_intent.get(intent, 0) + 1
                by_funnel_stage[funnel] = by_funnel_stage.get(funnel, 0) + 1
    
    return {
        'total_pages': total_pages,
        'pages_with_prompts': pages_with_prompts,
        'pages_without_prompts': total_pages - pages_with_prompts,
        'total_prompts': total_prompts,
        'avg_prompts_per_page': round(total_prompts / pages_with_prompts, 1) if pages_with_prompts > 0 else 0,
        'by_intent': by_intent,
        'by_funnel_stage': by_funnel_stage,
        'generation_progress': round((pages_with_prompts / total_pages) * 100, 1) if total_pages > 0 else 0,
    }


@router.get("/export/candidate-prompts")
async def export_candidate_prompts_csv(
    project_id: UUID = Query(..., description="Project ID to export prompts for"),
    include_pages_without_prompts: bool = Query(False, description="Include pages that don't have candidate prompts yet"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all candidate prompts for a project as CSV.
    
    The CSV is structured for easy processing with LLMs and includes:
    - Page information (URL, title, topic)
    - Prompt text and metadata
    - Intent classification and funnel stage
    - Audience persona and targeting info
    - Transaction scores for prioritization
    """
    # Get all pages with candidate prompts for this project
    query = select(Page).where(Page.project_id == project_id)
    
    if not include_pages_without_prompts:
        query = query.where(Page.candidate_prompts.isnot(None))
    
    result = await db.execute(query)
    pages = result.scalars().all()
    
    if not pages:
        raise HTTPException(
            status_code=404, 
            detail="No pages with candidate prompts found for this project"
        )
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        # Page info
        'page_url',
        'page_title',
        'page_topic',
        'page_summary',
        'meta_description',
        # Prompt info
        'prompt_text',
        'intent',
        'funnel_stage',
        'topic',
        'sub_topic',
        'audience_persona',
        'transaction_score',
        'citation_trigger',
        'reasoning',
        # Metadata
        'generated_at',
        'page_id',
    ])
    
    # Write data rows
    prompt_count = 0
    for page in pages:
        if not page.candidate_prompts:
            if include_pages_without_prompts:
                # Write a row for pages without prompts
                writer.writerow([
                    page.url,
                    page.title or '',
                    '',  # page_topic
                    '',  # page_summary
                    page.meta_description or '',
                    '',  # prompt_text
                    '',  # intent
                    '',  # funnel_stage
                    '',  # topic
                    '',  # sub_topic
                    '',  # audience_persona
                    '',  # transaction_score
                    '',  # citation_trigger
                    '',  # reasoning
                    '',  # generated_at
                    str(page.id),
                ])
            continue
        
        cached_data = page.candidate_prompts
        page_topic = cached_data.get('page_topic', '')
        page_summary = cached_data.get('page_summary', '')
        generated_at = cached_data.get('generated_at', '')
        
        for prompt in cached_data.get('prompts', []):
            prompt_count += 1
            writer.writerow([
                page.url,
                page.title or '',
                page_topic,
                page_summary,
                page.meta_description or '',
                prompt.get('text', ''),
                prompt.get('intent', ''),
                prompt.get('funnel_stage', ''),
                prompt.get('topic', ''),
                prompt.get('sub_topic', ''),
                prompt.get('audience_persona', prompt.get('target_audience', '')),
                prompt.get('transaction_score', ''),
                prompt.get('citation_trigger', ''),
                prompt.get('reasoning', ''),
                generated_at,
                str(page.id),
            ])
    
    # Get the CSV content
    output.seek(0)
    csv_content = output.getvalue()
    
    # Create filename with timestamp
    from datetime import datetime as dt
    timestamp = dt.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"candidate_prompts_{timestamp}.csv"
    
    logger.info(
        "Exported candidate prompts CSV",
        project_id=str(project_id),
        pages=len(pages),
        prompts=prompt_count,
    )
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'X-Total-Pages': str(len(pages)),
            'X-Total-Prompts': str(prompt_count),
        }
    )


@router.post("/generate-candidate-prompts-batch", response_model=dict)
async def generate_candidate_prompts_batch(
    project_id: UUID = Query(..., description="Project ID to generate prompts for"),
    regenerate: bool = Query(False, description="Regenerate prompts even if cached"),
    num_prompts: int = Query(5, ge=1, le=10, description="Number of prompts per page"),
    limit: Optional[int] = Query(None, description="Limit number of pages to process"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate candidate prompts for all pages in a project (batch operation).
    
    This is useful for populating prompts before exporting to CSV.
    Returns immediately with task status - generation happens in background.
    """
    from app.workers.nlp_tasks import generate_candidate_prompts_batch
    
    # Get pages that need prompts
    query = select(Page.id).where(Page.project_id == project_id)
    
    if not regenerate:
        query = query.where(Page.candidate_prompts.is_(None))
    
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    page_ids = [str(row[0]) for row in result.fetchall()]
    
    if not page_ids:
        return {
            "status": "no_pages",
            "message": "All pages already have candidate prompts" if not regenerate else "No pages found",
            "pages_queued": 0,
        }
    
    # Start background task
    task = generate_candidate_prompts_batch.delay(page_ids, num_prompts)
    
    return {
        "status": "processing",
        "task_id": task.id,
        "pages_queued": len(page_ids),
        "message": f"Generating candidate prompts for {len(page_ids)} pages",
    }


@router.get("/{page_id}/candidate-prompts", response_model=CandidatePromptsResponse)
async def get_candidate_prompts(
    page_id: UUID,
    regenerate: bool = Query(False, description="Force regeneration even if cached"),
    num_prompts: int = Query(5, ge=1, le=10, description="Number of prompts to generate"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate or retrieve candidate prompts for a page.
    
    These are high-impact, transactional prompts that would make LLMs cite this page.
    Results are cached in the database for performance.
    """
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Check for cached results
    if not regenerate and page.candidate_prompts:
        cached_data = page.candidate_prompts
        prompts = []
        for p in cached_data.get("prompts", []):
            prompts.append(CandidatePrompt(
                text=p.get("text", ""),
                transaction_score=p.get("transaction_score", 0.0),
                intent=p.get("intent", "unknown"),
                funnel_stage=p.get("funnel_stage"),
                topic=p.get("topic"),
                sub_topic=p.get("sub_topic"),
                audience_persona=p.get("audience_persona"),
                reasoning=p.get("reasoning", ""),
                target_audience=p.get("target_audience", p.get("audience_persona", "")),
                citation_trigger=p.get("citation_trigger"),
            ))
        
        return CandidatePromptsResponse(
            page_id=page.id,
            page_url=page.url,
            page_title=page.title,
            page_topic=cached_data.get("page_topic"),
            page_summary=cached_data.get("page_summary"),
            prompts=prompts,
            generated_at=cached_data.get("generated_at"),
            cached=True,
        )
    
    # Generate new candidate prompts
    if not azure_openai_service.enabled:
        raise HTTPException(
            status_code=400, 
            detail="AI service not available. Configure Azure OpenAI to generate candidate prompts."
        )
    
    result = azure_openai_service.generate_candidate_prompts(
        page_url=page.url,
        page_title=page.title or "",
        page_content=page.content or "",
        meta_description=page.meta_description,
        num_prompts=num_prompts,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate candidate prompts")
    
    # Cache the results
    page.candidate_prompts = result
    await db.commit()
    
    # Parse prompts
    prompts = []
    for p in result.get("prompts", []):
        prompts.append(CandidatePrompt(
            text=p.get("text", ""),
            transaction_score=p.get("transaction_score", 0.0),
            intent=p.get("intent", "unknown"),
            funnel_stage=p.get("funnel_stage"),
            topic=p.get("topic"),
            sub_topic=p.get("sub_topic"),
            audience_persona=p.get("audience_persona"),
            reasoning=p.get("reasoning", ""),
            target_audience=p.get("target_audience", p.get("audience_persona", "")),
            citation_trigger=p.get("citation_trigger"),
        ))
    
    return CandidatePromptsResponse(
        page_id=page.id,
        page_url=page.url,
        page_title=page.title,
        page_topic=result.get("page_topic"),
        page_summary=result.get("page_summary"),
        prompts=prompts,
        generated_at=result.get("generated_at"),
        cached=False,
    )


# Dynamic routes with {page_id} must come AFTER static routes like /orphan-pages
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
