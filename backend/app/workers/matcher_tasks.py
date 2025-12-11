"""Celery tasks for semantic matching."""

from typing import List
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.models.prompt import Prompt, MatchStatus
from app.models.page import Page
from app.models.match import Match, MatchType
from app.models.opportunity import Opportunity, OpportunityStatus, RecommendedAction
from app.services.matcher import matcher
from app.services.opportunity_generator import opportunity_generator

logger = get_logger(__name__)

# Create sync engine for Celery workers
sync_engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
SessionLocal = sessionmaker(bind=sync_engine)


@celery_app.task(bind=True, name="match_prompts_to_pages")
def match_prompts_to_pages(self, project_id: str, prompt_ids: List[str] = None):
    """
    Match prompts to pages and generate opportunities.
    
    Args:
        project_id: Project ID to match
        prompt_ids: Optional list of specific prompt IDs (otherwise all in project)
    """
    logger.info("Starting prompt-page matching", project_id=project_id)
    
    db = SessionLocal()
    
    try:
        # Get all pages for project
        pages = db.query(Page).filter(
            Page.project_id == UUID(project_id),
            Page.embedding.isnot(None)
        ).all()
        
        if not pages:
            logger.warning("No pages with embeddings found", project_id=project_id)
            return {"error": "No pages to match against"}
        
        # Prepare page data for matching
        page_data = [
            {
                "id": page.id,
                "embedding": page.embedding,
                "content": page.content or "",
                "title": page.title or "",
            }
            for page in pages
        ]
        
        # Get prompts to match
        from app.models.csv_import import CSVImport
        from app.models.project import Project
        
        # Get CSV imports for this project
        csv_imports = db.query(CSVImport).filter(
            CSVImport.project_id == UUID(project_id)
        ).all()
        
        import_ids = [ci.id for ci in csv_imports]
        
        query = db.query(Prompt).filter(
            Prompt.csv_import_id.in_(import_ids),
            Prompt.embedding.isnot(None)
        )
        
        if prompt_ids:
            query = query.filter(Prompt.id.in_([UUID(pid) for pid in prompt_ids]))
        
        prompts = query.all()
        
        logger.info(
            "Matching prompts to pages",
            prompt_count=len(prompts),
            page_count=len(pages)
        )
        
        matched_count = 0
        opportunity_count = 0
        
        for i, prompt in enumerate(prompts):
            try:
                # Find matches
                matches = matcher.find_matches_in_memory(
                    prompt.embedding,
                    prompt.raw_text,
                    page_data,
                    top_k=5
                )
                
                # Delete existing matches for this prompt
                db.query(Match).filter(Match.prompt_id == prompt.id).delete()
                
                # Create new matches
                best_score = None
                for match_result in matches:
                    match = Match(
                        prompt_id=prompt.id,
                        page_id=match_result.page_id,
                        similarity_score=match_result.similarity_score,
                        match_type=MatchType(match_result.match_type),
                        matched_snippet=match_result.matched_snippet,
                        rank=str(match_result.rank),
                    )
                    db.add(match)
                    
                    if best_score is None or match_result.similarity_score > best_score:
                        best_score = match_result.similarity_score
                
                # Update prompt match status
                prompt.match_status = MatchStatus(matcher.classify_match_status(best_score))
                prompt.best_match_score = best_score
                matched_count += 1
                
                # Generate opportunity for gaps and partial matches
                if prompt.match_status in [MatchStatus.GAP, MatchStatus.PARTIAL]:
                    # Delete existing opportunity
                    db.query(Opportunity).filter(Opportunity.prompt_id == prompt.id).delete()
                    
                    opp_data = opportunity_generator.generate_opportunity(
                        prompt_text=prompt.raw_text,
                        topic=prompt.topic,
                        popularity_score=prompt.popularity_score,
                        transaction_score=prompt.transaction_score,
                        sentiment_score=prompt.sentiment_score,
                        match_status=prompt.match_status.value,
                        best_match_score=best_score,
                        has_related_pages=bool(matches),
                    )
                    
                    opportunity = Opportunity(
                        prompt_id=prompt.id,
                        priority_score=opp_data.priority_score,
                        difficulty_score=opp_data.difficulty_score,
                        difficulty_factors=opp_data.difficulty_factors,
                        recommended_action=RecommendedAction(opp_data.recommended_action),
                        reason=opp_data.reason,
                        status=OpportunityStatus.NEW,
                        related_page_ids=[str(m.page_id) for m in matches[:3]],
                    )
                    db.add(opportunity)
                    opportunity_count += 1
                
                # Commit periodically
                if i % 50 == 0:
                    db.commit()
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "processed": i + 1,
                            "total": len(prompts),
                            "matched": matched_count,
                            "opportunities": opportunity_count,
                        }
                    )
                
            except Exception as e:
                logger.error("Error matching prompt", prompt_id=str(prompt.id), error=str(e))
        
        db.commit()
        
        logger.info(
            "Matching completed",
            matched=matched_count,
            opportunities=opportunity_count,
        )
        
        return {
            "status": "completed",
            "matched": matched_count,
            "opportunities": opportunity_count,
        }
        
    finally:
        db.close()


@celery_app.task(name="regenerate_opportunities")
def regenerate_opportunities(project_id: str):
    """
    Regenerate all opportunities for a project.
    """
    logger.info("Regenerating opportunities", project_id=project_id)
    
    db = SessionLocal()
    
    try:
        from app.models.csv_import import CSVImport
        
        # Get prompts with gaps or partial matches
        csv_imports = db.query(CSVImport).filter(
            CSVImport.project_id == UUID(project_id)
        ).all()
        
        import_ids = [ci.id for ci in csv_imports]
        
        prompts = db.query(Prompt).filter(
            Prompt.csv_import_id.in_(import_ids),
            Prompt.match_status.in_([MatchStatus.GAP, MatchStatus.PARTIAL])
        ).all()
        
        # Delete existing opportunities
        for prompt in prompts:
            db.query(Opportunity).filter(Opportunity.prompt_id == prompt.id).delete()
        
        db.commit()
        
        # Generate new opportunities
        opportunity_count = 0
        for prompt in prompts:
            matches = db.query(Match).filter(Match.prompt_id == prompt.id).all()
            
            opp_data = opportunity_generator.generate_opportunity(
                prompt_text=prompt.raw_text,
                topic=prompt.topic,
                popularity_score=prompt.popularity_score,
                transaction_score=prompt.transaction_score,
                sentiment_score=prompt.sentiment_score,
                match_status=prompt.match_status.value,
                best_match_score=prompt.best_match_score,
                has_related_pages=bool(matches),
            )
            
            opportunity = Opportunity(
                prompt_id=prompt.id,
                priority_score=opp_data.priority_score,
                difficulty_score=opp_data.difficulty_score,
                difficulty_factors=opp_data.difficulty_factors,
                recommended_action=RecommendedAction(opp_data.recommended_action),
                reason=opp_data.reason,
                status=OpportunityStatus.NEW,
                related_page_ids=[str(m.page_id) for m in matches[:3]],
            )
            db.add(opportunity)
            opportunity_count += 1
        
        db.commit()
        
        return {
            "status": "completed",
            "opportunities": opportunity_count,
        }
        
    finally:
        db.close()

