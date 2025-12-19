"""Prompt management API endpoints."""

import math
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.prompt import Prompt, IntentLabel, MatchStatus
from app.models.csv_import import CSVImport
from app.models.match import Match
from app.models.page import Page
from app.models.opportunity import Opportunity
from app.schemas.prompt import PromptResponse, PromptListResponse, PromptMatchInfo, CWVAssessment
from app.services.cwv import cwv_service

logger = get_logger(__name__)
router = APIRouter()


def safe_float(value: Optional[float]) -> Optional[float]:
    """Convert NaN/Inf to None for JSON serialization."""
    if value is None:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


@router.get("/", response_model=PromptListResponse)
async def list_prompts(
    project_id: Optional[UUID] = Query(None),
    csv_import_id: Optional[UUID] = Query(None),
    topic: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    intent_label: Optional[str] = Query(None),
    match_status: Optional[str] = Query(None),
    min_transaction_score: Optional[float] = Query(None, ge=0, le=1),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List prompts with filtering and pagination."""
    query = select(Prompt)
    
    # Filter by project
    if project_id:
        csv_imports = await db.execute(
            select(CSVImport.id).where(CSVImport.project_id == project_id)
        )
        import_ids = [row[0] for row in csv_imports]
        if import_ids:
            query = query.where(Prompt.csv_import_id.in_(import_ids))
        else:
            return PromptListResponse(prompts=[], total=0, page=page, page_size=page_size, pages=0)
    
    # Filter by CSV import
    if csv_import_id:
        query = query.where(Prompt.csv_import_id == csv_import_id)
    
    # Filter by topic
    if topic:
        query = query.where(Prompt.topic == topic)
    
    # Filter by category
    if category:
        query = query.where(Prompt.category == category)
    
    # Filter by language
    if language:
        query = query.where(Prompt.language == language)
    
    # Filter by intent
    if intent_label:
        query = query.where(Prompt.intent_label == IntentLabel(intent_label))
    
    # Filter by match status
    if match_status:
        query = query.where(Prompt.match_status == MatchStatus(match_status))
    
    # Filter by transaction score
    if min_transaction_score is not None:
        query = query.where(Prompt.transaction_score >= min_transaction_score)
    
    # Search
    if search:
        query = query.where(
            or_(
                Prompt.raw_text.ilike(f"%{search}%"),
                Prompt.topic.ilike(f"%{search}%"),
            )
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Get page
    query = query.order_by(Prompt.transaction_score.desc(), Prompt.popularity_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    prompts = result.scalars().all()
    
    # Get CWV assessment for best matching pages
    prompt_ids = [p.id for p in prompts]
    cwv_assessments = {}
    
    if prompt_ids:
        # Get best match for each prompt with page CWV data
        for p in prompts:
            if p.match_status and p.match_status.value != "pending":
                # Get best matching page
                best_match_result = await db.execute(
                    select(Match, Page)
                    .join(Page)
                    .where(Match.prompt_id == p.id)
                    .order_by(Match.similarity_score.desc())
                    .limit(1)
                )
                best_match = best_match_result.first()
                
                if best_match:
                    _, matched_page = best_match
                    if matched_page.cwv_data:
                        assessment = cwv_service.calculate_assessment(matched_page.cwv_data)
                        cwv_assessments[p.id] = CWVAssessment(**assessment)
    
    # Build response
    response_prompts = [
        PromptResponse(
            id=p.id,
            raw_text=p.raw_text,
            normalized_text=p.normalized_text,
            topic=p.topic,
            category=p.category,
            region=p.region,
            language=p.language,
            popularity_score=safe_float(p.popularity_score),
            sentiment_score=safe_float(p.sentiment_score),
            visibility_score=safe_float(p.visibility_score),
            intent_label=p.intent_label.value if p.intent_label else "informational",
            transaction_score=safe_float(p.transaction_score) or 0.0,
            match_status=p.match_status.value if p.match_status else "pending",
            best_match_score=safe_float(p.best_match_score),
            extra_data=p.extra_data or {},
            created_at=p.created_at,
            updated_at=p.updated_at,
            cwv_assessment=cwv_assessments.get(p.id),
        )
        for p in prompts
    ]
    
    pages_count = (total + page_size - 1) // page_size if total else 0
    
    return PromptListResponse(
        prompts=response_prompts,
        total=total or 0,
        page=page,
        page_size=page_size,
        pages=pages_count,
    )


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: UUID,
    include_matches: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Get prompt details with matches and opportunity."""
    prompt = await db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    response = PromptResponse(
        id=prompt.id,
        raw_text=prompt.raw_text,
        normalized_text=prompt.normalized_text,
        topic=prompt.topic,
        category=prompt.category,
        region=prompt.region,
        language=prompt.language,
        popularity_score=safe_float(prompt.popularity_score),
        sentiment_score=safe_float(prompt.sentiment_score),
        visibility_score=safe_float(prompt.visibility_score),
        intent_label=prompt.intent_label.value if prompt.intent_label else "informational",
        transaction_score=safe_float(prompt.transaction_score) or 0.0,
        match_status=prompt.match_status.value if prompt.match_status else "pending",
        best_match_score=safe_float(prompt.best_match_score),
        extra_data=prompt.extra_data or {},
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )
    
    if include_matches:
        # Get matches with page details
        matches_result = await db.execute(
            select(Match, Page)
            .join(Page)
            .where(Match.prompt_id == prompt_id)
            .order_by(Match.similarity_score.desc())
        )
        
        # Deduplicate by URL - keep highest scoring match for each URL
        seen_urls = set()
        deduplicated_matches = []
        for match, page in matches_result:
            if page.url not in seen_urls:
                seen_urls.add(page.url)
                deduplicated_matches.append(PromptMatchInfo(
                    page_id=match.page_id,
                    page_url=page.url,
                    page_title=page.title,
                    similarity_score=match.similarity_score,
                    match_type=match.match_type.value if match.match_type else "semantic",
                    matched_snippet=match.matched_snippet,
                ))
        
        response.matches = deduplicated_matches
        
        # Get opportunity
        opportunity = await db.execute(
            select(Opportunity).where(Opportunity.prompt_id == prompt_id)
        )
        opp = opportunity.scalar_one_or_none()
        if opp:
            response.opportunity = {
                "id": str(opp.id),
                "priority_score": opp.priority_score,
                "recommended_action": opp.recommended_action.value if opp.recommended_action else None,
                "reason": opp.reason,
                "status": opp.status.value if opp.status else "new",
            }
    
    return response


@router.get("/topics/list", response_model=dict)
async def list_topics(
    project_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get list of unique topics with counts."""
    query = select(Prompt.topic, func.count()).group_by(Prompt.topic)
    
    if project_id:
        csv_imports = await db.execute(
            select(CSVImport.id).where(CSVImport.project_id == project_id)
        )
        import_ids = [row[0] for row in csv_imports]
        if import_ids:
            query = query.where(Prompt.csv_import_id.in_(import_ids))
    
    result = await db.execute(query)
    topics = {str(row[0] or "Unknown"): row[1] for row in result}
    
    return {"topics": topics}


@router.get("/languages/list", response_model=dict)
async def list_languages(
    project_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get list of detected languages with counts."""
    query = select(Prompt.language, func.count()).group_by(Prompt.language)
    
    if project_id:
        csv_imports = await db.execute(
            select(CSVImport.id).where(CSVImport.project_id == project_id)
        )
        import_ids = [row[0] for row in csv_imports]
        if import_ids:
            query = query.where(Prompt.csv_import_id.in_(import_ids))
    
    result = await db.execute(query)
    languages = {str(row[0] or "unknown"): row[1] for row in result}
    
    return {"languages": languages}


@router.post("/reclassify-all", response_model=dict)
async def reclassify_all_prompts(
    project_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Re-run NLP classification for all prompts in a project."""
    from app.services.language_detector import language_detector
    from app.services.intent_classifier import intent_classifier
    
    query = select(Prompt)
    
    if project_id:
        csv_imports = await db.execute(
            select(CSVImport.id).where(CSVImport.project_id == project_id)
        )
        import_ids = [row[0] for row in csv_imports]
        if import_ids:
            query = query.where(Prompt.csv_import_id.in_(import_ids))
    
    result = await db.execute(query)
    prompts = result.scalars().all()
    
    updated_count = 0
    for prompt in prompts:
        # Re-detect language
        lang, _ = language_detector.detect(prompt.raw_text)
        prompt.language = lang
        
        # Re-classify intent
        intent_result = intent_classifier.classify(prompt.raw_text)
        prompt.intent_label = IntentLabel(intent_result.intent.value)
        prompt.transaction_score = intent_result.transaction_score
        
        updated_count += 1
    
    await db.commit()
    
    return {
        "message": f"Reclassified {updated_count} prompts",
        "updated_count": updated_count,
    }


@router.post("/reclassify-with-ai/")
async def reclassify_prompts_with_ai(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run intent classification using Azure OpenAI for all prompts in a project.
    This is more accurate than rule-based classification and correctly distinguishes
    transactional (ready to buy) from commercial (researching before purchase).
    """
    from app.workers.csv_tasks import reclassify_prompts_with_ai as reclassify_task
    from app.models.project import Project
    
    # Verify project exists
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get prompt count
    csv_imports = await db.execute(
        select(CSVImport.id).where(CSVImport.project_id == project_id)
    )
    import_ids = [row[0] for row in csv_imports]
    
    count_query = select(func.count()).select_from(Prompt).where(
        Prompt.csv_import_id.in_(import_ids)
    )
    prompt_count = await db.scalar(count_query)
    
    # Trigger the reclassification task
    task = reclassify_task.delay(str(project_id))
    
    logger.info("Started AI reclassification", project_id=str(project_id), task_id=task.id)
    
    return {
        "status": "started",
        "message": f"AI reclassification started for {prompt_count} prompts",
        "task_id": task.id,
        "project_id": str(project_id),
        "prompt_count": prompt_count,
    }


@router.get("/{prompt_id}/explain-intent")
async def explain_intent(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get explanation of why this intent was classified using LLM when available."""
    from app.services.intent_classifier import intent_classifier
    from app.services.azure_openai import azure_openai_service
    
    prompt = await db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Run rule-based classification to get signals
    result = intent_classifier.classify(prompt.raw_text)
    
    # Clean up signals for display
    clean_signals = []
    for s in result.signals:
        if s.startswith("Matched:"):
            pattern = s.replace("Matched: ", "")
            readable = pattern.replace("\\b", "").replace("\\s+", " ").replace("\\s*", " ")
            readable = readable.replace("(", "").replace(")", "").replace("?", "")
            readable = readable.strip()
            if readable:
                clean_signals.append(readable)
        else:
            clean_signals.append(s)
    
    # Try to get LLM-enhanced explanation
    llm_explanation = None
    llm_analysis = None
    classification_method = "rule-based"
    
    if azure_openai_service.enabled:
        try:
            llm_result = azure_openai_service.classify_intent(prompt.raw_text)
            if llm_result:
                classification_method = "ai-enhanced"
                llm_analysis = {
                    "intent": llm_result.get("intent", result.intent.value),
                    "confidence": llm_result.get("confidence", result.confidence),
                    "transaction_score": llm_result.get("transaction_score", result.transaction_score),
                    "reasoning": llm_result.get("reasoning", ""),
                }
                llm_explanation = llm_result.get("reasoning", "")
        except Exception as e:
            logger.warning(f"LLM intent explanation failed: {e}")
    
    # Generate explanation (prefer LLM if available)
    if llm_explanation:
        explanation = llm_explanation
    else:
        explanation = _generate_intent_explanation(result.intent.value, result.signals, result.transaction_score)
    
    return {
        "prompt_text": prompt.raw_text,
        "intent": llm_analysis["intent"] if llm_analysis else result.intent.value,
        "transaction_score": llm_analysis["transaction_score"] if llm_analysis else result.transaction_score,
        "confidence": llm_analysis["confidence"] if llm_analysis else result.confidence,
        "signals": clean_signals,
        "explanation": explanation,
        "classification_method": classification_method,
        "llm_analysis": llm_analysis,
    }


def _generate_intent_explanation(intent: str, signals: list, transaction_score: float) -> str:
    """Generate a human-readable explanation for the classification."""
    intent_descriptions = {
        "transactional": "This query indicates purchase or booking intent",
        "commercial": "This query shows research behavior before a potential purchase",
        "comparison": "This query explicitly compares options for decision-making",
        "informational": "This query seeks to learn or understand something",
        "navigational": "This query aims to reach a specific page or service",
        "exploratory": "This query is browsing a topic without specific goals",
        "procedural": "This query asks for step-by-step instructions",
        "troubleshooting": "This query seeks to solve a problem or fix an issue",
        "opinion_seeking": "This query asks for subjective opinions or recommendations",
        "emotional": "This query expresses strong sentiment or feelings",
        "regulatory": "This query asks about rules, policies, or regulations",
        "brand_monitoring": "This query relates to brand news or mentions",
        "meta": "This query asks for content generation or AI tasks",
    }
    
    base = intent_descriptions.get(intent, "This query was classified based on pattern analysis")
    
    if signals:
        # Convert regex patterns to readable keywords
        readable_signals = []
        for s in signals:
            if s.startswith("Matched:"):
                pattern = s.replace("Matched: ", "")
                # Clean up regex to readable text
                readable = pattern.replace("\\b", "").replace("\\s+", " ").replace("\\s*", " ")
                readable = readable.replace("(", "").replace(")", "").replace("?", "")
                readable = readable.strip()
                if readable:
                    readable_signals.append(f'"{readable}"')
            else:
                readable_signals.append(s)
        
        if readable_signals:
            base += f". Detected keywords: {', '.join(readable_signals[:3])}"
    
    if transaction_score >= 0.7:
        base += ". High likelihood of conversion."
    elif transaction_score >= 0.4:
        base += ". Moderate purchase consideration."
    
    return base


@router.post("/{prompt_id}/reclassify", response_model=PromptResponse)
async def reclassify_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Re-run NLP classification for a single prompt."""
    from app.services.language_detector import language_detector
    from app.services.intent_classifier import intent_classifier
    from app.services.embeddings import embedding_service
    
    prompt = await db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Re-detect language
    lang, _ = language_detector.detect(prompt.raw_text)
    prompt.language = lang
    
    # Re-classify intent
    intent_result = intent_classifier.classify(prompt.raw_text)
    prompt.intent_label = IntentLabel(intent_result.intent.value)
    prompt.transaction_score = intent_result.transaction_score
    
    # Re-generate embedding
    embedding = embedding_service.encode(prompt.raw_text)
    prompt.embedding = embedding
    
    await db.commit()
    await db.refresh(prompt)
    
    return PromptResponse(
        id=prompt.id,
        raw_text=prompt.raw_text,
        normalized_text=prompt.normalized_text,
        topic=prompt.topic,
        category=prompt.category,
        region=prompt.region,
        language=prompt.language,
        popularity_score=safe_float(prompt.popularity_score),
        sentiment_score=safe_float(prompt.sentiment_score),
        visibility_score=safe_float(prompt.visibility_score),
        intent_label=prompt.intent_label.value if prompt.intent_label else "informational",
        transaction_score=safe_float(prompt.transaction_score) or 0.0,
        match_status=prompt.match_status.value if prompt.match_status else "pending",
        best_match_score=safe_float(prompt.best_match_score),
        extra_data=prompt.extra_data or {},
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )
