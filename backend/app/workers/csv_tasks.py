"""Celery tasks for CSV processing."""

import json
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.models.csv_import import CSVImport, ImportStatus
from app.models.prompt import Prompt, IntentLabel, MatchStatus
from app.services.csv_parser import csv_parser, sanitize_for_json
from app.services.language_detector import language_detector
from app.services.intent_classifier import intent_classifier, IntentType
from app.services.embeddings import embedding_service

logger = get_logger(__name__)

# Create sync engine for Celery workers
sync_engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
SessionLocal = sessionmaker(bind=sync_engine)


def get_db_session() -> Session:
    """Get a sync database session for Celery tasks."""
    return SessionLocal()


@celery_app.task(bind=True, name="process_csv_import")
def process_csv_import(self, import_id: str):
    """
    Process a CSV import: parse rows, detect language, classify intent, generate embeddings.
    """
    logger.info("Starting CSV processing", import_id=import_id)
    
    db = get_db_session()
    
    try:
        csv_import = db.query(CSVImport).filter(CSVImport.id == UUID(import_id)).first()
        if not csv_import:
            logger.error("CSV import not found", import_id=import_id)
            return {"error": "Import not found"}
        
        csv_import.status = ImportStatus.PROCESSING
        db.commit()
        
        column_mapping = csv_import.column_mapping
        total_processed = 0
        total_failed = 0
        total_updated = 0
        batch_texts = []
        batch_prompts = []
        
        # Get all existing imports for this project for deduplication
        project_imports = db.query(CSVImport).filter(
            CSVImport.project_id == csv_import.project_id
        ).all()
        project_import_ids = [imp.id for imp in project_imports]
        
        # Process in batches
        for batch in csv_parser.iterate_rows(csv_import.file_path, column_mapping, batch_size=50):
            for row_data in batch:
                try:
                    # Sanitize extra_data for JSON storage
                    extra_data = sanitize_for_json(row_data.get("extra_data", {}))
                    normalized_text = row_data["raw_text"].lower().strip()
                    
                    # Check for existing prompt with same text in this project (deduplication)
                    existing_prompt = db.query(Prompt).filter(
                        Prompt.csv_import_id.in_(project_import_ids),
                        Prompt.normalized_text == normalized_text
                    ).first()
                    
                    if existing_prompt:
                        # Update existing prompt
                        prompt = existing_prompt
                        prompt.csv_import_id = csv_import.id  # Move to new import
                        prompt.topic = row_data.get("topic") or prompt.topic
                        prompt.category = row_data.get("category") or prompt.category
                        prompt.region = row_data.get("region") or prompt.region
                        prompt.popularity_score = row_data.get("popularity_score") or prompt.popularity_score
                        prompt.sentiment_score = row_data.get("sentiment_score") or prompt.sentiment_score
                        prompt.visibility_score = row_data.get("visibility_score") or prompt.visibility_score
                        prompt.extra_data = extra_data or prompt.extra_data
                        total_updated += 1
                    else:
                        # Create new prompt record
                        prompt = Prompt(
                            csv_import_id=csv_import.id,
                            raw_text=row_data["raw_text"],
                            normalized_text=normalized_text,
                            topic=row_data.get("topic"),
                            category=row_data.get("category"),
                            region=row_data.get("region"),
                            popularity_score=row_data.get("popularity_score"),
                            sentiment_score=row_data.get("sentiment_score"),
                            visibility_score=row_data.get("visibility_score"),
                            extra_data=extra_data,
                            match_status=MatchStatus.PENDING,
                        )
                    
                    # Detect language
                    lang, lang_confidence = language_detector.detect(row_data["raw_text"])
                    prompt.language = lang
                    
                    # Classify intent
                    intent_result = intent_classifier.classify(row_data["raw_text"])
                    prompt.intent_label = IntentLabel(intent_result.intent.value)
                    prompt.transaction_score = intent_result.transaction_score
                    
                    # Track if this is a new prompt or update
                    is_new = existing_prompt is None
                    
                    batch_texts.append(row_data["raw_text"])
                    batch_prompts.append((prompt, is_new))
                    total_processed += 1
                    
                except Exception as e:
                    logger.warning("Failed to process row", error=str(e))
                    total_failed += 1
            
            # Generate embeddings for batch
            if batch_texts:
                embeddings = embedding_service.encode_batch(batch_texts)
                for (prompt, is_new), embedding in zip(batch_prompts, embeddings):
                    prompt.embedding = embedding
                    # Only add new prompts (existing ones are already in session)
                    if is_new:
                        db.add(prompt)
                
                batch_texts = []
                batch_prompts = []
            
            # Update progress
            csv_import.processed_rows = total_processed
            csv_import.failed_rows = total_failed
            db.commit()
            
            # Report progress to Celery
            self.update_state(
                state="PROGRESS",
                meta={
                    "processed": total_processed,
                    "failed": total_failed,
                    "total": csv_import.total_rows,
                }
            )
        
        # Final commit
        csv_import.status = ImportStatus.COMPLETED
        csv_import.processed_rows = total_processed
        csv_import.failed_rows = total_failed
        db.commit()
        
        logger.info(
            "CSV processing completed",
            import_id=import_id,
            processed=total_processed,
            updated=total_updated,
            failed=total_failed,
        )
        
        return {
            "status": "completed",
            "processed": total_processed,
            "updated": total_updated,
            "new": total_processed - total_updated,
            "failed": total_failed,
        }
        
    except Exception as e:
        logger.error("CSV processing failed", import_id=import_id, error=str(e))
        
        if csv_import:
            csv_import.status = ImportStatus.FAILED
            csv_import.error_message = str(e)[:1000]
            db.commit()
        
        raise
    
    finally:
        db.close()


@celery_app.task(name="reprocess_prompts_nlp")
def reprocess_prompts_nlp(import_id: str):
    """
    Reprocess NLP (language, intent, embeddings) for all prompts in an import.
    Useful when models or rules are updated.
    """
    logger.info("Reprocessing prompts NLP", import_id=import_id)
    
    db = get_db_session()
    
    try:
        prompts = db.query(Prompt).filter(
            Prompt.csv_import_id == UUID(import_id)
        ).all()
        
        batch_size = 50
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i+batch_size]
            texts = [p.raw_text for p in batch]
            
            # Update language and intent
            for prompt in batch:
                lang, _ = language_detector.detect(prompt.raw_text)
                prompt.language = lang
                
                intent_result = intent_classifier.classify(prompt.raw_text)
                prompt.intent_label = IntentLabel(intent_result.intent.value)
                prompt.transaction_score = intent_result.transaction_score
            
            # Update embeddings
            embeddings = embedding_service.encode_batch(texts)
            for prompt, embedding in zip(batch, embeddings):
                prompt.embedding = embedding
            
            db.commit()
        
        return {"status": "completed", "processed": len(prompts)}
        
    finally:
        db.close()

