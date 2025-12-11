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

