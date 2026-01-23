"""Celery tasks for NLP processing."""

from typing import List
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.models.prompt import Prompt, IntentLabel
from app.services.language_detector import language_detector
from app.services.intent_classifier import intent_classifier
from app.services.embeddings import embedding_service

logger = get_logger(__name__)

# Create sync engine for Celery workers
sync_engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
SessionLocal = sessionmaker(bind=sync_engine)


@celery_app.task(name="classify_intent_batch")
def classify_intent_batch(prompt_ids: List[str]):
    """
    Classify intent for a batch of prompts.
    """
    logger.info("Classifying intent batch", count=len(prompt_ids))
    
    db = SessionLocal()
    
    try:
        prompts = db.query(Prompt).filter(
            Prompt.id.in_([UUID(pid) for pid in prompt_ids])
        ).all()
        
        for prompt in prompts:
            intent_result = intent_classifier.classify(prompt.raw_text)
            prompt.intent_label = IntentLabel(intent_result.intent.value)
            prompt.transaction_score = intent_result.transaction_score
        
        db.commit()
        
        return {"status": "completed", "processed": len(prompts)}
        
    finally:
        db.close()


@celery_app.task(name="detect_language_batch")
def detect_language_batch(prompt_ids: List[str]):
    """
    Detect language for a batch of prompts.
    """
    logger.info("Detecting language batch", count=len(prompt_ids))
    
    db = SessionLocal()
    
    try:
        prompts = db.query(Prompt).filter(
            Prompt.id.in_([UUID(pid) for pid in prompt_ids])
        ).all()
        
        for prompt in prompts:
            lang, confidence = language_detector.detect(prompt.raw_text)
            prompt.language = lang
        
        db.commit()
        
        return {"status": "completed", "processed": len(prompts)}
        
    finally:
        db.close()


@celery_app.task(name="generate_embeddings_batch")
def generate_embeddings_batch(prompt_ids: List[str]):
    """
    Generate embeddings for a batch of prompts.
    """
    logger.info("Generating embeddings batch", count=len(prompt_ids))
    
    db = SessionLocal()
    
    try:
        prompts = db.query(Prompt).filter(
            Prompt.id.in_([UUID(pid) for pid in prompt_ids])
        ).all()
        
        texts = [p.raw_text for p in prompts]
        embeddings = embedding_service.encode_batch(texts)
        
        for prompt, embedding in zip(prompts, embeddings):
            prompt.embedding = embedding
        
        db.commit()
        
        return {"status": "completed", "processed": len(prompts)}
        
    finally:
        db.close()


@celery_app.task(name="generate_page_embeddings_batch")
def generate_page_embeddings_batch(page_ids: List[str]):
    """
    Generate embeddings for a batch of pages.
    """
    from app.models.page import Page
    
    logger.info("Generating page embeddings batch", count=len(page_ids))
    
    db = SessionLocal()
    
    try:
        pages = db.query(Page).filter(
            Page.id.in_([UUID(pid) for pid in page_ids])
        ).all()
        
        # Combine title and content for embedding
        texts = []
        for page in pages:
            text_parts = []
            if page.title:
                text_parts.append(page.title)
            if page.meta_description:
                text_parts.append(page.meta_description)
            if page.content:
                # Use first 1000 chars of content
                text_parts.append(page.content[:1000])
            texts.append(" ".join(text_parts))
        
        embeddings = embedding_service.encode_batch(texts)
        
        for page, embedding in zip(pages, embeddings):
            page.embedding = embedding
        
        db.commit()
        
        return {"status": "completed", "processed": len(pages)}
        
    finally:
        db.close()


def _collect_existing_prompts(db: Session, project_id: UUID, exclude_page_ids: List[UUID] | None = None) -> set:
    """
    Collect all existing prompt texts from a project for deduplication.
    Returns a set of normalized (lowercase) prompt texts.
    """
    from app.models.page import Page
    
    query = db.query(Page).filter(
        Page.project_id == project_id,
        Page.candidate_prompts.isnot(None)
    )
    
    if exclude_page_ids:
        query = query.filter(Page.id.notin_(exclude_page_ids))
    
    existing_prompts = set()
    for page in query.all():
        prompts_data = page.candidate_prompts
        if prompts_data and "prompts" in prompts_data:
            for prompt in prompts_data["prompts"]:
                if "text" in prompt and prompt["text"]:
                    existing_prompts.add(prompt["text"].lower().strip())
    
    return existing_prompts


def _deduplicate_prompts(result: dict, existing_prompts: set) -> dict:
    """
    Remove prompts that already exist in the project.
    """
    if not result or "prompts" not in result:
        return result
    
    unique_prompts = []
    for prompt in result["prompts"]:
        if "text" in prompt and prompt["text"]:
            normalized = prompt["text"].lower().strip()
            if normalized not in existing_prompts:
                unique_prompts.append(prompt)
                existing_prompts.add(normalized)  # Add to set to prevent duplicates within batch
    
    result["prompts"] = unique_prompts
    return result


@celery_app.task(name="generate_candidate_prompts_batch", bind=True)
def generate_candidate_prompts_batch(self, page_ids: List[str], num_prompts: int = 5, example_prompts: list | None = None):
    """
    Generate candidate prompts for a batch of pages using Azure OpenAI.
    
    This generates casual, human-like prompts that would make LLMs cite each page.
    Results are cached in the page's candidate_prompts JSONB field.
    
    Args:
        example_prompts: Optional list of human prompt examples for few-shot learning
    """
    from app.models.page import Page
    from app.services.azure_openai import azure_openai_service
    import time
    
    logger.info("Generating candidate prompts batch", count=len(page_ids), num_prompts=num_prompts, has_examples=bool(example_prompts))
    
    if not azure_openai_service.enabled:
        logger.error("Azure OpenAI service not enabled")
        return {"status": "error", "message": "Azure OpenAI service not configured"}
    
    db = SessionLocal()
    
    try:
        pages = db.query(Page).filter(
            Page.id.in_([UUID(pid) for pid in page_ids])
        ).all()
        
        if not pages:
            return {"status": "completed", "processed": 0, "failed": 0, "total": 0}
        
        # Get project ID from first page and collect existing prompts for deduplication
        project_id = pages[0].project_id
        page_uuid_list = [UUID(pid) for pid in page_ids]
        existing_prompts = _collect_existing_prompts(db, project_id, exclude_page_ids=page_uuid_list)
        logger.info("Collected existing prompts for deduplication", count=len(existing_prompts))
        
        processed = 0
        failed = 0
        duplicates_removed = 0
        
        for i, page in enumerate(pages):
            try:
                # Generate candidate prompts (include SEO data and examples if available)
                result = azure_openai_service.generate_candidate_prompts(
                    page_url=page.url,
                    page_title=page.title or "",
                    page_content=page.content or "",
                    meta_description=page.meta_description,
                    seo_data=page.seo_data,  # Pass SEO keyword data if available
                    example_prompts=example_prompts,  # Pass human examples for few-shot learning
                    num_prompts=num_prompts,
                )
                
                if result:
                    # Count prompts before deduplication
                    original_count = len(result.get("prompts", []))
                    
                    # Deduplicate against existing prompts in project
                    result = _deduplicate_prompts(result, existing_prompts)
                    
                    # Track duplicates removed
                    new_count = len(result.get("prompts", []))
                    duplicates_removed += (original_count - new_count)
                    
                    page.candidate_prompts = result
                    processed += 1
                    logger.debug("Generated prompts for page", url=page.url, prompts=new_count, duplicates_removed=original_count - new_count)
                else:
                    failed += 1
                    logger.warning("Failed to generate prompts for page", url=page.url)
                
                # Commit every 10 pages
                if (i + 1) % 10 == 0:
                    db.commit()
                    
                    # Update task state for progress tracking
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "processed": processed,
                            "failed": failed,
                            "total": len(pages),
                            "current_url": page.url,
                            "duplicates_removed": duplicates_removed,
                        }
                    )
                
                # Rate limiting - avoid hitting API too fast
                time.sleep(0.5)
                
            except Exception as e:
                failed += 1
                logger.error("Error generating prompts for page", url=page.url, error=str(e))
        
        # Final commit
        db.commit()
        
        logger.info(
            "Candidate prompts batch completed",
            processed=processed,
            failed=failed,
            total=len(pages),
            duplicates_removed=duplicates_removed,
        )
        
        return {
            "status": "completed",
            "processed": processed,
            "failed": failed,
            "total": len(pages),
            "duplicates_removed": duplicates_removed,
        }
        
    except Exception as e:
        logger.error("Candidate prompts batch failed", error=str(e))
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()

