"""Project management API endpoints."""

from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
from datetime import datetime

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.project import Project
from app.models.csv_import import CSVImport
from app.models.prompt import Prompt
from app.models.page import Page
from app.models.opportunity import Opportunity
from app.models.crawl_job import CrawlJob, CrawlStatus
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    db_project = Project(
        id=uuid4(),
        name=project.name,
        description=project.description,
        target_domains=project.target_domains,
        crawl_config=project.crawl_config.model_dump() if project.crawl_config else {},
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    
    return ProjectResponse(
        id=db_project.id,
        name=db_project.name,
        description=db_project.description,
        target_domains=db_project.target_domains,
        crawl_config=db_project.crawl_config,
        created_at=db_project.created_at,
        updated_at=db_project.updated_at,
    )


@router.get("/", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all projects with statistics."""
    # Count total
    count_query = select(func.count()).select_from(Project)
    total = await db.scalar(count_query)
    
    # Get projects
    query = select(Project).order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Get statistics for each project
    response_projects = []
    for project in projects:
        # Count prompts
        prompt_count = await db.scalar(
            select(func.count())
            .select_from(Prompt)
            .join(CSVImport)
            .where(CSVImport.project_id == project.id)
        )
        
        # Count pages
        page_count = await db.scalar(
            select(func.count())
            .select_from(Page)
            .where(Page.project_id == project.id)
        )
        
        # Count opportunities
        opp_count = await db.scalar(
            select(func.count())
            .select_from(Opportunity)
            .join(Prompt)
            .join(CSVImport)
            .where(CSVImport.project_id == project.id)
        )
        
        response_projects.append(ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            target_domains=project.target_domains,
            crawl_config=project.crawl_config,
            created_at=project.created_at,
            updated_at=project.updated_at,
            prompt_count=prompt_count or 0,
            page_count=page_count or 0,
            opportunity_count=opp_count or 0,
        ))
    
    return {
        "projects": response_projects,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get project details with statistics."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get statistics
    prompt_count = await db.scalar(
        select(func.count())
        .select_from(Prompt)
        .join(CSVImport)
        .where(CSVImport.project_id == project.id)
    )
    
    page_count = await db.scalar(
        select(func.count())
        .select_from(Page)
        .where(Page.project_id == project.id)
    )
    
    opp_count = await db.scalar(
        select(func.count())
        .select_from(Opportunity)
        .join(Prompt)
        .join(CSVImport)
        .where(CSVImport.project_id == project.id)
    )
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        target_domains=project.target_domains,
        crawl_config=project.crawl_config,
        created_at=project.created_at,
        updated_at=project.updated_at,
        prompt_count=prompt_count or 0,
        page_count=page_count or 0,
        opportunity_count=opp_count or 0,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update project settings."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if update.name is not None:
        project.name = update.name
    if update.description is not None:
        project.description = update.description
    if update.target_domains is not None:
        project.target_domains = update.target_domains
    if update.crawl_config is not None:
        project.crawl_config = update.crawl_config.model_dump()
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        target_domains=project.target_domains,
        crawl_config=project.crawl_config,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a project and all associated data."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await db.delete(project)
    await db.commit()
    
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/crawl", response_model=dict)
async def start_crawl(
    project_id: UUID,
    start_urls: Optional[list] = None,
    db: AsyncSession = Depends(get_db),
):
    """Start a new crawl job for the project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Use provided URLs or project's target domains
    urls = start_urls or [f"https://{d}" for d in project.target_domains]
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs to crawl")
    
    # Create crawl job
    crawl_job = CrawlJob(
        id=uuid4(),
        project_id=project_id,
        status=CrawlStatus.PENDING,
        config={
            "start_urls": urls,
            **project.crawl_config,
        },
    )
    db.add(crawl_job)
    await db.commit()
    
    # Start Celery task
    from app.workers.crawler_tasks import crawl_website
    task = crawl_website.delay(str(crawl_job.id))
    
    crawl_job.celery_task_id = task.id
    await db.commit()
    
    return {
        "crawl_job_id": str(crawl_job.id),
        "task_id": task.id,
        "status": "started",
    }


@router.post("/{project_id}/crawl-from-csv", response_model=dict)
async def crawl_from_csv(
    project_id: UUID,
    file: UploadFile = File(..., description="CSV file with URLs and SEO data (Ahrefs/SEMrush format)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a crawl job from a CSV file containing URLs and SEO keyword data.
    
    The CSV should have columns like:
    - URL: The page URL to crawl
    - Current top keyword / top_keyword: Primary keyword
    - Current top keyword: Volume / volume: Search volume
    - Current traffic / traffic: Monthly traffic
    
    This will:
    1. Extract URLs from the CSV
    2. Crawl each URL
    3. Store SEO keyword data alongside each page
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Read and parse CSV
    content = await file.read()
    
    # Try to decode - handle UTF-16 (Ahrefs) or UTF-8
    try:
        text = content.decode('utf-16')
    except (UnicodeDecodeError, UnicodeError):
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('utf-8')
    
    lines = text.strip().split('\n')
    if not lines:
        raise HTTPException(status_code=400, detail="Empty CSV file")
    
    # Detect delimiter
    delimiter = '\t' if '\t' in lines[0] else ','
    reader = csv.DictReader(lines, delimiter=delimiter)
    
    def normalize_col(col):
        return col.strip().strip('"').lower().replace(' ', '_')
    
    # Parse URLs and SEO data
    urls_to_crawl = []
    seo_data_by_url = {}
    
    for row in reader:
        row_normalized = {normalize_col(k): v.strip().strip('"') for k, v in row.items()}
        
        url = row_normalized.get('url', '')
        if not url:
            continue
        
        urls_to_crawl.append(url)
        
        # Extract SEO data
        seo_data = {'imported_at': datetime.utcnow().isoformat()}
        
        # Top keyword
        top_kw = row_normalized.get('current_top_keyword') or row_normalized.get('top_keyword') or row_normalized.get('keyword')
        if top_kw:
            seo_data['top_keyword'] = top_kw
        
        # Keyword volume
        kw_vol = row_normalized.get('current_top_keyword:_volume') or row_normalized.get('volume') or row_normalized.get('search_volume')
        if kw_vol:
            try:
                seo_data['keyword_volume'] = int(float(kw_vol.replace(',', '')))
            except (ValueError, AttributeError):
                pass
        
        # Traffic
        traffic = row_normalized.get('current_traffic') or row_normalized.get('traffic')
        if traffic:
            try:
                seo_data['traffic'] = int(float(traffic.replace(',', '')))
            except (ValueError, AttributeError):
                pass
        
        # Traffic value
        traffic_val = row_normalized.get('current_traffic_value') or row_normalized.get('traffic_value')
        if traffic_val:
            try:
                seo_data['traffic_value'] = float(traffic_val.replace(',', ''))
            except (ValueError, AttributeError):
                pass
        
        # Keywords count
        kw_count = row_normalized.get('current_#_of_keywords') or row_normalized.get('keywords') or row_normalized.get('keywords_count')
        if kw_count:
            try:
                seo_data['keywords_count'] = int(float(kw_count.replace(',', '')))
            except (ValueError, AttributeError):
                pass
        
        # Referring domains
        ref_domains = row_normalized.get('current_referring_domains') or row_normalized.get('referring_domains')
        if ref_domains:
            try:
                seo_data['referring_domains'] = int(float(ref_domains.replace(',', '')))
            except (ValueError, AttributeError):
                pass
        
        # URL Rating
        ur = row_normalized.get('ur') or row_normalized.get('url_rating')
        if ur:
            try:
                seo_data['url_rating'] = float(ur)
            except (ValueError, AttributeError):
                pass
        
        if len(seo_data) > 1:  # More than just imported_at
            seo_data_by_url[url] = seo_data
            # Also store without trailing slash for matching
            seo_data_by_url[url.rstrip('/')] = seo_data
    
    if not urls_to_crawl:
        raise HTTPException(status_code=400, detail="No valid URLs found in CSV")
    
    # Create crawl job with SEO data in config
    crawl_job = CrawlJob(
        id=uuid4(),
        project_id=project_id,
        status=CrawlStatus.PENDING,
        config={
            "start_urls": urls_to_crawl,
            "seo_data": seo_data_by_url,  # Store SEO data for later use
            **project.crawl_config,
        },
    )
    db.add(crawl_job)
    await db.commit()
    
    # Start Celery task
    from app.workers.crawler_tasks import crawl_url_list_with_seo
    task = crawl_url_list_with_seo.delay(str(crawl_job.id), urls_to_crawl, seo_data_by_url)
    
    crawl_job.celery_task_id = task.id
    await db.commit()
    
    logger.info(
        "Started CSV crawl with SEO data",
        project_id=str(project_id),
        urls=len(urls_to_crawl),
        urls_with_seo=len(seo_data_by_url),
    )
    
    return {
        "crawl_job_id": str(crawl_job.id),
        "task_id": task.id,
        "status": "started",
        "urls_to_crawl": len(urls_to_crawl),
        "urls_with_seo_data": len(seo_data_by_url) // 2,  # Divide by 2 because we store with/without trailing slash
    }


@router.post("/{project_id}/match", response_model=dict)
async def run_matching(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Run prompt-to-page matching for the project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Start matching task
    from app.workers.matcher_tasks import match_prompts_to_pages
    task = match_prompts_to_pages.delay(str(project_id))
    
    return {
        "task_id": task.id,
        "status": "started",
    }


@router.get("/{project_id}/stats", response_model=dict)
async def get_project_stats(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed statistics for a project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get CSV imports for this project
    csv_imports = await db.execute(
        select(CSVImport).where(CSVImport.project_id == project_id)
    )
    import_ids = [ci.id for ci in csv_imports.scalars().all()]
    
    if not import_ids:
        return {
            "total_prompts": 0,
            "total_pages": 0,
            "by_intent": {},
            "by_match_status": {},
            "by_language": {},
            "opportunities_by_status": {},
            "opportunities_by_action": {},
            "high_priority_count": 0,
        }
    
    # Get prompts stats
    total_prompts = await db.scalar(
        select(func.count()).select_from(Prompt).where(Prompt.csv_import_id.in_(import_ids))
    )
    
    # By intent
    intent_stats = await db.execute(
        select(Prompt.intent_label, func.count())
        .where(Prompt.csv_import_id.in_(import_ids))
        .group_by(Prompt.intent_label)
    )
    by_intent = {(row[0].value if row[0] else "unknown"): row[1] for row in intent_stats}
    
    # By match status
    match_stats = await db.execute(
        select(Prompt.match_status, func.count())
        .where(Prompt.csv_import_id.in_(import_ids))
        .group_by(Prompt.match_status)
    )
    by_match_status = {(row[0].value if row[0] else "pending"): row[1] for row in match_stats}
    
    # By language
    lang_stats = await db.execute(
        select(Prompt.language, func.count())
        .where(Prompt.csv_import_id.in_(import_ids))
        .group_by(Prompt.language)
    )
    by_language = {str(row[0] or "unknown"): row[1] for row in lang_stats}
    
    # Pages count
    total_pages = await db.scalar(
        select(func.count()).select_from(Page).where(Page.project_id == project_id)
    )
    
    # Opportunities by status
    opp_status_stats = await db.execute(
        select(Opportunity.status, func.count())
        .join(Prompt)
        .where(Prompt.csv_import_id.in_(import_ids))
        .group_by(Opportunity.status)
    )
    opportunities_by_status = {(row[0].value if row[0] else "new"): row[1] for row in opp_status_stats}
    
    # Opportunities by action
    opp_action_stats = await db.execute(
        select(Opportunity.recommended_action, func.count())
        .join(Prompt)
        .where(Prompt.csv_import_id.in_(import_ids))
        .group_by(Opportunity.recommended_action)
    )
    opportunities_by_action = {(row[0].value if row[0] else "other"): row[1] for row in opp_action_stats}
    
    # High priority opportunities (priority_score >= 0.7)
    high_priority_count = await db.scalar(
        select(func.count())
        .select_from(Opportunity)
        .join(Prompt)
        .where(Prompt.csv_import_id.in_(import_ids))
        .where(Opportunity.priority_score >= 0.7)
    )
    
    # High transaction/buying intent prompts (transaction_score >= 0.6)
    high_transaction_count = await db.scalar(
        select(func.count())
        .select_from(Prompt)
        .where(Prompt.csv_import_id.in_(import_ids))
        .where(Prompt.transaction_score >= 0.6)
    )
    
    return {
        "total_prompts": total_prompts or 0,
        "total_pages": total_pages or 0,
        "by_intent": by_intent,
        "by_match_status": by_match_status,
        "by_language": by_language,
        "opportunities_by_status": opportunities_by_status,
        "opportunities_by_action": opportunities_by_action,
        "high_priority_count": high_priority_count or 0,
        "high_transaction_count": high_transaction_count or 0,
    }
