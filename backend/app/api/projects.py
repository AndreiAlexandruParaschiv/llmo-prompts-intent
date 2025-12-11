"""Project management API endpoints."""

from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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
