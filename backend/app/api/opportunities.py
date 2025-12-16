"""Opportunity management API endpoints."""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import csv
import io
import json
import math

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.opportunity import Opportunity, OpportunityStatus, RecommendedAction
from app.models.prompt import Prompt
from app.models.csv_import import CSVImport
from app.schemas.opportunity import OpportunityResponse, OpportunityListResponse, OpportunityUpdate

logger = get_logger(__name__)
router = APIRouter()


def safe_float(value: Optional[float]) -> Optional[float]:
    """Convert NaN/Inf to None for JSON serialization."""
    if value is None:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


@router.get("/", response_model=OpportunityListResponse)
async def list_opportunities(
    project_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    recommended_action: Optional[str] = Query(None),
    min_priority: Optional[float] = Query(None, ge=0, le=1),
    max_priority: Optional[float] = Query(None, ge=0, le=1),
    max_difficulty: Optional[float] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List opportunities with filtering."""
    query = select(Opportunity, Prompt).join(Prompt)
    
    # Filter by project
    if project_id:
        csv_imports = await db.execute(
            select(CSVImport.id).where(CSVImport.project_id == project_id)
        )
        import_ids = [row[0] for row in csv_imports]
        if import_ids:
            query = query.where(Prompt.csv_import_id.in_(import_ids))
        else:
            return OpportunityListResponse(
                opportunities=[], total=0, page=page, page_size=page_size,
                by_status={}, by_action={}
            )
    
    # Filters
    if status:
        query = query.where(Opportunity.status == OpportunityStatus(status))
    
    if recommended_action:
        query = query.where(Opportunity.recommended_action == RecommendedAction(recommended_action))
    
    if min_priority is not None:
        query = query.where(Opportunity.priority_score >= min_priority)
    
    if max_priority is not None:
        query = query.where(Opportunity.priority_score <= max_priority)
    
    if max_difficulty is not None:
        query = query.where(Opportunity.difficulty_score <= max_difficulty)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Get page
    query = query.order_by(Opportunity.priority_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Build response
    response_opportunities = []
    for opp, prompt in rows:
        response_opportunities.append(OpportunityResponse(
            id=opp.id,
            prompt_id=opp.prompt_id,
            priority_score=safe_float(opp.priority_score) or 0.0,
            difficulty_score=safe_float(opp.difficulty_score),
            difficulty_factors=opp.difficulty_factors or {},
            recommended_action=opp.recommended_action.value if opp.recommended_action else "other",
            reason=opp.reason,
            status=opp.status.value if opp.status else "new",
            assigned_to=opp.assigned_to,
            notes=opp.notes,
            content_suggestion=opp.content_suggestion or {},
            related_page_ids=opp.related_page_ids or [],
            created_at=opp.created_at,
            updated_at=opp.updated_at,
            prompt_text=prompt.raw_text,
            prompt_topic=prompt.topic,
            prompt_intent=prompt.intent_label.value if prompt.intent_label else None,
            prompt_transaction_score=safe_float(prompt.transaction_score),
            prompt_popularity_score=safe_float(prompt.popularity_score),
            prompt_sentiment_score=safe_float(prompt.sentiment_score),
        ))
    
    # Get stats for filters
    by_status = {}
    by_action = {}
    
    if project_id and import_ids:
        status_stats = await db.execute(
            select(Opportunity.status, func.count())
            .join(Prompt)
            .where(Prompt.csv_import_id.in_(import_ids))
            .group_by(Opportunity.status)
        )
        by_status = {str(row[0].value if row[0] else "new"): row[1] for row in status_stats}
        
        action_stats = await db.execute(
            select(Opportunity.recommended_action, func.count())
            .join(Prompt)
            .where(Prompt.csv_import_id.in_(import_ids))
            .group_by(Opportunity.recommended_action)
        )
        by_action = {str(row[0].value if row[0] else "other"): row[1] for row in action_stats}
    
    return OpportunityListResponse(
        opportunities=response_opportunities,
        total=total or 0,
        page=page,
        page_size=page_size,
        by_status=by_status,
        by_action=by_action,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get opportunity details."""
    result = await db.execute(
        select(Opportunity, Prompt)
        .join(Prompt)
        .where(Opportunity.id == opportunity_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    opp, prompt = row
    
    return OpportunityResponse(
        id=opp.id,
        prompt_id=opp.prompt_id,
        priority_score=safe_float(opp.priority_score) or 0.0,
        difficulty_score=safe_float(opp.difficulty_score),
        difficulty_factors=opp.difficulty_factors or {},
        recommended_action=opp.recommended_action.value if opp.recommended_action else "other",
        reason=opp.reason,
        status=opp.status.value if opp.status else "new",
        assigned_to=opp.assigned_to,
        notes=opp.notes,
        content_suggestion=opp.content_suggestion or {},
        related_page_ids=opp.related_page_ids or [],
        created_at=opp.created_at,
        updated_at=opp.updated_at,
        prompt_text=prompt.raw_text,
        prompt_topic=prompt.topic,
        prompt_intent=prompt.intent_label.value if prompt.intent_label else None,
        prompt_transaction_score=safe_float(prompt.transaction_score),
        prompt_popularity_score=safe_float(prompt.popularity_score),
        prompt_sentiment_score=safe_float(prompt.sentiment_score),
    )


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: UUID,
    update: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update opportunity status, assignment, or notes."""
    opp = await db.get(Opportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    if update.status is not None:
        opp.status = OpportunityStatus(update.status)
    if update.assigned_to is not None:
        opp.assigned_to = update.assigned_to
    if update.notes is not None:
        opp.notes = update.notes
    
    await db.commit()
    await db.refresh(opp)
    
    # Get prompt for response
    prompt = await db.get(Prompt, opp.prompt_id)
    
    return OpportunityResponse(
        id=opp.id,
        prompt_id=opp.prompt_id,
        priority_score=safe_float(opp.priority_score) or 0.0,
        difficulty_score=safe_float(opp.difficulty_score),
        difficulty_factors=opp.difficulty_factors or {},
        recommended_action=opp.recommended_action.value if opp.recommended_action else "other",
        reason=opp.reason,
        status=opp.status.value if opp.status else "new",
        assigned_to=opp.assigned_to,
        notes=opp.notes,
        content_suggestion=opp.content_suggestion or {},
        related_page_ids=opp.related_page_ids or [],
        created_at=opp.created_at,
        updated_at=opp.updated_at,
        prompt_text=prompt.raw_text if prompt else None,
        prompt_topic=prompt.topic if prompt else None,
        prompt_intent=prompt.intent_label.value if prompt and prompt.intent_label else None,
        prompt_transaction_score=safe_float(prompt.transaction_score) if prompt else None,
        prompt_popularity_score=safe_float(prompt.popularity_score) if prompt else None,
        prompt_sentiment_score=safe_float(prompt.sentiment_score) if prompt else None,
    )


@router.post("/{opportunity_id}/generate-suggestion", response_model=OpportunityResponse)
async def generate_opportunity_suggestion(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate AI content suggestion for a single opportunity."""
    from app.services.azure_openai import AzureOpenAIService
    
    # Get opportunity with prompt
    result = await db.execute(
        select(Opportunity, Prompt)
        .join(Prompt)
        .where(Opportunity.id == opportunity_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    opp, prompt = row
    
    # Generate AI suggestion
    azure_service = AzureOpenAIService()
    suggestion = azure_service.generate_content_suggestion(
        prompt_text=prompt.raw_text,
        intent=prompt.intent_label.value if prompt.intent_label else "informational",
        match_status=opp.recommended_action.value if opp.recommended_action else "create_content",
        existing_content_snippets=None
    )
    
    if suggestion:
        opp.content_suggestion = suggestion
        await db.commit()
        await db.refresh(opp)
        logger.info(f"Generated AI suggestion for opportunity {opportunity_id}")
    else:
        logger.warning(f"Failed to generate AI suggestion for opportunity {opportunity_id}")
    
    return OpportunityResponse(
        id=opp.id,
        prompt_id=opp.prompt_id,
        priority_score=safe_float(opp.priority_score) or 0.0,
        difficulty_score=safe_float(opp.difficulty_score),
        difficulty_factors=opp.difficulty_factors or {},
        recommended_action=opp.recommended_action.value if opp.recommended_action else "other",
        reason=opp.reason,
        status=opp.status.value if opp.status else "new",
        assigned_to=opp.assigned_to,
        notes=opp.notes,
        content_suggestion=opp.content_suggestion or {},
        related_page_ids=opp.related_page_ids or [],
        created_at=opp.created_at,
        updated_at=opp.updated_at,
        prompt_text=prompt.raw_text,
        prompt_topic=prompt.topic,
        prompt_intent=prompt.intent_label.value if prompt.intent_label else None,
        prompt_transaction_score=safe_float(prompt.transaction_score),
        prompt_popularity_score=safe_float(prompt.popularity_score),
        prompt_sentiment_score=safe_float(prompt.sentiment_score),
    )


@router.get("/export/csv")
async def export_opportunities_csv(
    project_id: UUID,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export opportunities to CSV."""
    query = select(Opportunity, Prompt).join(Prompt)
    
    csv_imports = await db.execute(
        select(CSVImport.id).where(CSVImport.project_id == project_id)
    )
    import_ids = [row[0] for row in csv_imports]
    
    if import_ids:
        query = query.where(Prompt.csv_import_id.in_(import_ids))
    
    if status:
        query = query.where(Opportunity.status == OpportunityStatus(status))
    
    query = query.order_by(Opportunity.priority_score.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Priority Score", "Prompt", "Topic", "Intent", "Transaction Score",
        "Recommended Action", "Reason", "Status", "Difficulty Score",
        "AI Suggested Title", "AI Content Type", "AI Outline", "AI Call to Action", "AI Keywords", "AI Priority Reason"
    ])
    
    # Data
    for opp, prompt in rows:
        # Extract AI suggestion fields
        suggestion = opp.content_suggestion or {}
        ai_title = suggestion.get("title", "")
        ai_content_type = suggestion.get("content_type", "")
        ai_outline = "; ".join(suggestion.get("outline", [])) if isinstance(suggestion.get("outline"), list) else str(suggestion.get("outline", ""))
        ai_cta = suggestion.get("cta", "")
        ai_keywords = "; ".join(suggestion.get("keywords", [])) if isinstance(suggestion.get("keywords"), list) else str(suggestion.get("keywords", ""))
        ai_priority_reason = suggestion.get("priority_reason", "")
        
        writer.writerow([
            f"{opp.priority_score:.2f}",
            prompt.raw_text,
            prompt.topic or "",
            prompt.intent_label.value if prompt.intent_label else "",
            f"{prompt.transaction_score:.2f}" if prompt.transaction_score else "",
            opp.recommended_action.value if opp.recommended_action else "",
            opp.reason or "",
            opp.status.value if opp.status else "",
            f"{opp.difficulty_score:.2f}" if opp.difficulty_score else "",
            ai_title,
            ai_content_type,
            ai_outline,
            ai_cta,
            ai_keywords,
            ai_priority_reason,
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=opportunities.csv"}
    )


@router.get("/export/json")
async def export_opportunities_json(
    project_id: UUID,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export opportunities to JSON."""
    query = select(Opportunity, Prompt).join(Prompt)
    
    csv_imports = await db.execute(
        select(CSVImport.id).where(CSVImport.project_id == project_id)
    )
    import_ids = [row[0] for row in csv_imports]
    
    if import_ids:
        query = query.where(Prompt.csv_import_id.in_(import_ids))
    
    if status:
        query = query.where(Opportunity.status == OpportunityStatus(status))
    
    query = query.order_by(Opportunity.priority_score.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    # Build JSON
    data = []
    for opp, prompt in rows:
        data.append({
            "id": str(opp.id),
            "priority_score": opp.priority_score,
            "prompt": prompt.raw_text,
            "topic": prompt.topic,
            "intent": prompt.intent_label.value if prompt.intent_label else None,
            "transaction_score": prompt.transaction_score,
            "recommended_action": opp.recommended_action.value if opp.recommended_action else None,
            "reason": opp.reason,
            "status": opp.status.value if opp.status else None,
            "difficulty_score": opp.difficulty_score,
            "difficulty_factors": opp.difficulty_factors,
        })
    
    output = io.StringIO()
    json.dump(data, output, indent=2)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=opportunities.json"}
    )


@router.post("/{project_id}/regenerate-suggestions/")
async def regenerate_content_suggestions(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate AI content suggestions for all opportunities in a project.
    Useful when Azure OpenAI is newly configured or suggestions are missing.
    """
    from app.workers.matcher_tasks import regenerate_content_suggestions as regenerate_task
    
    # Verify project exists
    from app.models.project import Project
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get opportunity count for this project
    from app.models.opportunity import Opportunity
    
    csv_imports_result = await db.execute(
        select(CSVImport.id).where(CSVImport.project_id == project_id)
    )
    import_ids = [row[0] for row in csv_imports_result]
    
    opp_count = 0
    if import_ids:
        from app.models.prompt import Prompt
        prompt_ids_result = await db.execute(
            select(Prompt.id).where(Prompt.csv_import_id.in_(import_ids))
        )
        prompt_ids = [row[0] for row in prompt_ids_result]
        if prompt_ids:
            opp_count_result = await db.execute(
                select(func.count()).select_from(Opportunity).where(Opportunity.prompt_id.in_(prompt_ids))
            )
            opp_count = opp_count_result.scalar() or 0
    
    # Trigger the regeneration task
    task = regenerate_task.delay(str(project_id))
    
    logger.info("Started content suggestion regeneration", project_id=str(project_id), task_id=task.id)
    
    return {
        "status": "started",
        "message": "Content suggestion regeneration started",
        "task_id": task.id,
        "project_id": str(project_id),
        "opportunity_count": opp_count,
    }
