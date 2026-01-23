"""Celery tasks for web crawling."""

import asyncio
import time
from typing import List, Set
from uuid import UUID
from urllib.parse import urlparse
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.models.crawl_job import CrawlJob, CrawlStatus
from app.models.page import Page
from app.services.crawler import crawler
from app.services.embeddings import embedding_service

logger = get_logger(__name__)

# Create sync engine for Celery workers
sync_engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
SessionLocal = sessionmaker(bind=sync_engine)


def run_async(coro):
    """Helper to run async code in sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="crawl_website")
def crawl_website(self, crawl_job_id: str):
    """
    Crawl a website based on crawl job configuration.
    """
    logger.info("Starting website crawl", job_id=crawl_job_id)
    
    db = SessionLocal()
    
    try:
        crawl_job = db.query(CrawlJob).filter(CrawlJob.id == UUID(crawl_job_id)).first()
        if not crawl_job:
            logger.error("Crawl job not found", job_id=crawl_job_id)
            return {"error": "Crawl job not found"}
        
        # Update status
        crawl_job.status = CrawlStatus.RUNNING
        crawl_job.started_at = datetime.utcnow()
        db.commit()
        
        config = crawl_job.config or {}
        start_urls = config.get("start_urls", [])
        max_pages = config.get("max_pages", settings.CRAWLER_MAX_PAGES)
        rate_limit = config.get("rate_limit", settings.CRAWLER_RATE_LIMIT)
        allowed_paths = config.get("allowed_paths", [])
        excluded_paths = config.get("excluded_paths", [])
        
        if not start_urls:
            crawl_job.status = CrawlStatus.FAILED
            crawl_job.error_message = "No start URLs provided"
            db.commit()
            return {"error": "No start URLs"}
        
        # Track visited URLs
        visited: Set[str] = set()
        to_visit: List[str] = list(start_urls)
        crawl_job.total_urls = len(to_visit)
        pages_created = []
        errors = []
        
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            
            # Skip if already visited
            if url in visited:
                continue
            
            # Check path restrictions
            if not crawler.is_allowed_path(url, allowed_paths, excluded_paths):
                continue
            
            visited.add(url)
            
            try:
                # Crawl page
                page_data = run_async(crawler.crawl_page(url))
                
                if page_data.get("error"):
                    errors.append({
                        "url": url,
                        "error": page_data["error"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    crawl_job.failed_urls += 1
                else:
                    # Check if URL already exists for this project (deduplication)
                    existing_page = db.query(Page).filter(
                        Page.project_id == crawl_job.project_id,
                        Page.url == page_data["url"]
                    ).first()
                    
                    if existing_page:
                        # Update existing page
                        page = existing_page
                        page.crawl_job_id = crawl_job.id
                        page.canonical_url = page_data.get("canonical_url")
                        page.status_code = page_data.get("status_code")
                        page.content_type = page_data.get("content_type")
                        page.title = page_data.get("title")
                        page.meta_description = page_data.get("meta_description")
                        page.content = page_data.get("content")
                        page.word_count = str(page_data.get("word_count", 0))
                        page.html_snapshot_path = page_data.get("html_snapshot_path")
                        page.structured_data = page_data.get("structured_data", [])
                        page.hreflang_tags = page_data.get("hreflang_tags", [])
                        page.crawled_at = page_data.get("crawled_at")
                    else:
                        # Create new page record
                        page = Page(
                            project_id=crawl_job.project_id,
                            crawl_job_id=crawl_job.id,
                            url=page_data["url"],
                            canonical_url=page_data.get("canonical_url"),
                            status_code=page_data.get("status_code"),
                            content_type=page_data.get("content_type"),
                            title=page_data.get("title"),
                            meta_description=page_data.get("meta_description"),
                            content=page_data.get("content"),
                            word_count=str(page_data.get("word_count", 0)),
                            html_snapshot_path=page_data.get("html_snapshot_path"),
                            structured_data=page_data.get("structured_data", []),
                            hreflang_tags=page_data.get("hreflang_tags", []),
                            crawled_at=page_data.get("crawled_at"),
                        )
                        db.add(page)
                    
                    # Generate embedding immediately for this page
                    text_parts = []
                    if page.title:
                        text_parts.append(page.title)
                    if page.meta_description:
                        text_parts.append(page.meta_description)
                    if page.content:
                        text_parts.append(page.content[:2000])
                    if text_parts:
                        page.embedding = embedding_service.encode(" ".join(text_parts))
                    
                    pages_created.append(page)
                    crawl_job.crawled_urls += 1
                    
                    # Extract links for further crawling
                    if page_data.get("html_snapshot_path"):
                        with open(page_data["html_snapshot_path"], "r") as f:
                            html = f.read()
                        links = crawler.extract_links(html, url)
                        
                        # Add same-domain links to queue
                        base_domain = urlparse(url).netloc
                        for link in links:
                            if urlparse(link).netloc == base_domain and link not in visited:
                                to_visit.append(link)
                
                crawl_job.total_urls = len(visited) + len(to_visit)
                db.commit()
                
                # Report progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "crawled": crawl_job.crawled_urls,
                        "failed": crawl_job.failed_urls,
                        "total": crawl_job.total_urls,
                        "current_url": url,
                    }
                )
                
                # Rate limiting
                time.sleep(rate_limit)
                
            except Exception as e:
                logger.error("Error crawling URL", url=url, error=str(e))
                errors.append({
                    "url": url,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                crawl_job.failed_urls += 1
                db.commit()
        
        # Complete job (embeddings are now generated per-page above)
        crawl_job.status = CrawlStatus.COMPLETED
        crawl_job.completed_at = datetime.utcnow()
        crawl_job.errors = errors
        db.commit()
        
        logger.info(
            "Crawl completed",
            job_id=crawl_job_id,
            crawled=crawl_job.crawled_urls,
            failed=crawl_job.failed_urls,
        )
        
        return {
            "status": "completed",
            "crawled": crawl_job.crawled_urls,
            "failed": crawl_job.failed_urls,
            "pages_created": len(pages_created),
        }
        
    except Exception as e:
        logger.error("Crawl job failed", job_id=crawl_job_id, error=str(e))
        
        if crawl_job:
            crawl_job.status = CrawlStatus.FAILED
            crawl_job.error_message = str(e)[:1000]
            crawl_job.completed_at = datetime.utcnow()
            db.commit()
        
        raise
    
    finally:
        db.close()


@celery_app.task(name="crawl_single_url")
def crawl_single_url(project_id: str, url: str):
    """
    Crawl a single URL and add to project pages.
    """
    logger.info("Crawling single URL", project_id=project_id, url=url)
    
    db = SessionLocal()
    
    try:
        page_data = run_async(crawler.crawl_page(url))
        
        if page_data.get("error"):
            return {"error": page_data["error"]}
        
        # Generate embedding
        text_parts = []
        if page_data.get("title"):
            text_parts.append(page_data["title"])
        if page_data.get("meta_description"):
            text_parts.append(page_data["meta_description"])
        if page_data.get("content"):
            text_parts.append(page_data["content"][:2000])
        
        embedding = embedding_service.encode(" ".join(text_parts))
        
        # Check if URL already exists for this project (deduplication)
        existing_page = db.query(Page).filter(
            Page.project_id == UUID(project_id),
            Page.url == page_data["url"]
        ).first()
        
        if existing_page:
            # Update existing page
            existing_page.canonical_url = page_data.get("canonical_url")
            existing_page.status_code = page_data.get("status_code")
            existing_page.content_type = page_data.get("content_type")
            existing_page.title = page_data.get("title")
            existing_page.meta_description = page_data.get("meta_description")
            existing_page.content = page_data.get("content")
            existing_page.word_count = str(page_data.get("word_count", 0))
            existing_page.html_snapshot_path = page_data.get("html_snapshot_path")
            existing_page.structured_data = page_data.get("structured_data", [])
            existing_page.hreflang_tags = page_data.get("hreflang_tags", [])
            existing_page.embedding = embedding
            existing_page.crawled_at = page_data.get("crawled_at")
            db.commit()
            return {"status": "updated", "page_id": str(existing_page.id)}
        
        # Create new page record
        page = Page(
            project_id=UUID(project_id),
            url=page_data["url"],
            canonical_url=page_data.get("canonical_url"),
            status_code=page_data.get("status_code"),
            content_type=page_data.get("content_type"),
            title=page_data.get("title"),
            meta_description=page_data.get("meta_description"),
            content=page_data.get("content"),
            word_count=str(page_data.get("word_count", 0)),
            html_snapshot_path=page_data.get("html_snapshot_path"),
            structured_data=page_data.get("structured_data", []),
            hreflang_tags=page_data.get("hreflang_tags", []),
            embedding=embedding,
            crawled_at=page_data.get("crawled_at"),
        )
        db.add(page)
        db.commit()
        
        return {"status": "completed", "page_id": str(page.id)}
        
    finally:
        db.close()


@celery_app.task(bind=True, name="crawl_url_list_with_seo")
def crawl_url_list_with_seo(self, crawl_job_id: str, urls: List[str], seo_data_by_url: dict | None = None):
    """
    Crawl a list of URLs and store SEO keyword data alongside each page.
    
    Args:
        crawl_job_id: The crawl job ID
        urls: List of URLs to crawl
        seo_data_by_url: Dict mapping URL -> SEO data (keywords, traffic, etc.)
    """
    logger.info("Starting URL list crawl with SEO data", job_id=crawl_job_id, url_count=len(urls))
    
    seo_data_by_url = seo_data_by_url or {}
    
    db = SessionLocal()
    
    try:
        crawl_job = db.query(CrawlJob).filter(CrawlJob.id == UUID(crawl_job_id)).first()
        if not crawl_job:
            logger.error("Crawl job not found", job_id=crawl_job_id)
            return {"error": "Crawl job not found"}
        
        # Update status
        crawl_job.status = CrawlStatus.RUNNING
        crawl_job.started_at = datetime.utcnow()
        crawl_job.total_urls = len(urls)
        db.commit()
        
        pages_created = []
        errors = []
        
        for i, url in enumerate(urls):
            try:
                # Crawl page
                page_data = run_async(crawler.crawl_page(url))
                
                if page_data.get("error"):
                    errors.append({
                        "url": url,
                        "error": page_data["error"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    crawl_job.failed_urls += 1
                else:
                    # Get SEO data for this URL (try with and without trailing slash)
                    seo_data = seo_data_by_url.get(url) or seo_data_by_url.get(url.rstrip('/')) or seo_data_by_url.get(url + '/')
                    
                    # Check if URL already exists for this project (deduplication)
                    existing_page = db.query(Page).filter(
                        Page.project_id == crawl_job.project_id,
                        Page.url == page_data["url"]
                    ).first()
                    
                    if existing_page:
                        # Update existing page
                        page = existing_page
                        page.crawl_job_id = crawl_job.id
                        page.canonical_url = page_data.get("canonical_url")
                        page.status_code = page_data.get("status_code")
                        page.content_type = page_data.get("content_type")
                        page.title = page_data.get("title")
                        page.meta_description = page_data.get("meta_description")
                        page.content = page_data.get("content")
                        page.word_count = str(page_data.get("word_count", 0))
                        page.html_snapshot_path = page_data.get("html_snapshot_path")
                        page.structured_data = page_data.get("structured_data", [])
                        page.hreflang_tags = page_data.get("hreflang_tags", [])
                        page.crawled_at = page_data.get("crawled_at")
                        # Store SEO data
                        if seo_data:
                            page.seo_data = seo_data
                    else:
                        # Create new page record
                        page = Page(
                            project_id=crawl_job.project_id,
                            crawl_job_id=crawl_job.id,
                            url=page_data["url"],
                            canonical_url=page_data.get("canonical_url"),
                            status_code=page_data.get("status_code"),
                            content_type=page_data.get("content_type"),
                            title=page_data.get("title"),
                            meta_description=page_data.get("meta_description"),
                            content=page_data.get("content"),
                            word_count=str(page_data.get("word_count", 0)),
                            html_snapshot_path=page_data.get("html_snapshot_path"),
                            structured_data=page_data.get("structured_data", []),
                            hreflang_tags=page_data.get("hreflang_tags", []),
                            crawled_at=page_data.get("crawled_at"),
                            seo_data=seo_data,  # Store SEO data
                        )
                        db.add(page)
                    
                    # Generate embedding immediately for this page
                    text_parts = []
                    if page.title:
                        text_parts.append(page.title)
                    if page.meta_description:
                        text_parts.append(page.meta_description)
                    if page.content:
                        text_parts.append(page.content[:2000])
                    if text_parts:
                        page.embedding = embedding_service.encode(" ".join(text_parts))
                    
                    pages_created.append(page)
                    crawl_job.crawled_urls += 1
                
                db.commit()
                
                # Report progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "crawled": crawl_job.crawled_urls,
                        "failed": crawl_job.failed_urls,
                        "total": crawl_job.total_urls,
                        "current_url": url,
                        "progress_percent": int((i + 1) / len(urls) * 100),
                    }
                )
                
                # Rate limiting
                time.sleep(settings.CRAWLER_RATE_LIMIT)
                
            except Exception as e:
                logger.error("Error crawling URL", url=url, error=str(e))
                errors.append({
                    "url": url,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                crawl_job.failed_urls += 1
                db.commit()
        
        # Complete job
        crawl_job.status = CrawlStatus.COMPLETED
        crawl_job.completed_at = datetime.utcnow()
        crawl_job.errors = errors
        db.commit()
        
        logger.info(
            "URL list crawl with SEO completed",
            job_id=crawl_job_id,
            crawled=crawl_job.crawled_urls,
            failed=crawl_job.failed_urls,
        )
        
        return {
            "status": "completed",
            "crawled": crawl_job.crawled_urls,
            "failed": crawl_job.failed_urls,
            "pages_created": len(pages_created),
        }
        
    except Exception as e:
        logger.error("URL list crawl with SEO failed", job_id=crawl_job_id, error=str(e))
        
        if crawl_job:
            crawl_job.status = CrawlStatus.FAILED
            crawl_job.error_message = str(e)[:1000]
            crawl_job.completed_at = datetime.utcnow()
            db.commit()
        
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True, name="crawl_url_list")
def crawl_url_list(self, crawl_job_id: str, urls: List[str]):
    """
    Crawl a specific list of URLs (more efficient than full site crawl).
    """
    logger.info("Starting URL list crawl", job_id=crawl_job_id, url_count=len(urls))
    
    db = SessionLocal()
    
    try:
        crawl_job = db.query(CrawlJob).filter(CrawlJob.id == UUID(crawl_job_id)).first()
        if not crawl_job:
            logger.error("Crawl job not found", job_id=crawl_job_id)
            return {"error": "Crawl job not found"}
        
        # Update status
        crawl_job.status = CrawlStatus.RUNNING
        crawl_job.started_at = datetime.utcnow()
        crawl_job.total_urls = len(urls)
        db.commit()
        
        pages_created = []
        errors = []
        
        for i, url in enumerate(urls):
            try:
                # Crawl page
                page_data = run_async(crawler.crawl_page(url))
                
                if page_data.get("error"):
                    errors.append({
                        "url": url,
                        "error": page_data["error"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    crawl_job.failed_urls += 1
                else:
                    # Check if URL already exists for this project (deduplication)
                    existing_page = db.query(Page).filter(
                        Page.project_id == crawl_job.project_id,
                        Page.url == page_data["url"]
                    ).first()
                    
                    if existing_page:
                        # Update existing page
                        page = existing_page
                        page.crawl_job_id = crawl_job.id
                        page.canonical_url = page_data.get("canonical_url")
                        page.status_code = page_data.get("status_code")
                        page.content_type = page_data.get("content_type")
                        page.title = page_data.get("title")
                        page.meta_description = page_data.get("meta_description")
                        page.content = page_data.get("content")
                        page.word_count = str(page_data.get("word_count", 0))
                        page.html_snapshot_path = page_data.get("html_snapshot_path")
                        page.structured_data = page_data.get("structured_data", [])
                        page.hreflang_tags = page_data.get("hreflang_tags", [])
                        page.crawled_at = page_data.get("crawled_at")
                    else:
                        # Create new page record
                        page = Page(
                            project_id=crawl_job.project_id,
                            crawl_job_id=crawl_job.id,
                            url=page_data["url"],
                            canonical_url=page_data.get("canonical_url"),
                            status_code=page_data.get("status_code"),
                            content_type=page_data.get("content_type"),
                            title=page_data.get("title"),
                            meta_description=page_data.get("meta_description"),
                            content=page_data.get("content"),
                            word_count=str(page_data.get("word_count", 0)),
                            html_snapshot_path=page_data.get("html_snapshot_path"),
                            structured_data=page_data.get("structured_data", []),
                            hreflang_tags=page_data.get("hreflang_tags", []),
                            crawled_at=page_data.get("crawled_at"),
                        )
                        db.add(page)
                    
                    # Generate embedding immediately for this page
                    text_parts = []
                    if page.title:
                        text_parts.append(page.title)
                    if page.meta_description:
                        text_parts.append(page.meta_description)
                    if page.content:
                        text_parts.append(page.content[:2000])
                    if text_parts:
                        page.embedding = embedding_service.encode(" ".join(text_parts))
                    
                    pages_created.append(page)
                    crawl_job.crawled_urls += 1
                
                db.commit()
                
                # Report progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "crawled": crawl_job.crawled_urls,
                        "failed": crawl_job.failed_urls,
                        "total": crawl_job.total_urls,
                        "current_url": url,
                        "progress_percent": int((i + 1) / len(urls) * 100),
                    }
                )
                
                # Rate limiting
                time.sleep(settings.CRAWLER_RATE_LIMIT)
                
            except Exception as e:
                logger.error("Error crawling URL", url=url, error=str(e))
                errors.append({
                    "url": url,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                crawl_job.failed_urls += 1
                db.commit()
        
        # Complete job (embeddings are now generated per-page above)
        crawl_job.status = CrawlStatus.COMPLETED
        crawl_job.completed_at = datetime.utcnow()
        crawl_job.errors = errors
        db.commit()
        
        logger.info(
            "URL list crawl completed",
            job_id=crawl_job_id,
            crawled=crawl_job.crawled_urls,
            failed=crawl_job.failed_urls,
        )
        
        return {
            "status": "completed",
            "crawled": crawl_job.crawled_urls,
            "failed": crawl_job.failed_urls,
            "pages_created": len(pages_created),
        }
        
    except Exception as e:
        logger.error("URL list crawl failed", job_id=crawl_job_id, error=str(e))
        
        if crawl_job:
            crawl_job.status = CrawlStatus.FAILED
            crawl_job.error_message = str(e)[:1000]
            crawl_job.completed_at = datetime.utcnow()
            db.commit()
        
        raise
    
    finally:
        db.close()

