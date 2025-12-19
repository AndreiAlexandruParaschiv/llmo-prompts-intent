"""Core Web Vitals API endpoints."""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.page import Page
from app.services.cwv import cwv_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/page/{page_id}")
async def get_page_cwv(
    page_id: UUID,
    refresh: bool = Query(False, description="Force refresh from PageSpeed API"),
    strategy: str = Query("mobile", description="mobile or desktop"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Core Web Vitals for a specific page.
    Returns cached data if available, otherwise fetches from PageSpeed Insights.
    """
    # Get the page
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Check for cached data
    if not refresh and page.cwv_data:
        # Check if data is fresh (less than 24 hours old)
        fetched_at = page.cwv_data.get("fetched_at")
        if fetched_at:
            try:
                fetch_time = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - fetch_time).total_seconds() / 3600
                if age_hours < 24:
                    return {
                        "page_id": str(page_id),
                        "url": page.url,
                        "cached": True,
                        "cwv": page.cwv_data,
                    }
            except (ValueError, TypeError):
                pass
    
    # Fetch fresh CWV data
    metrics = await cwv_service.fetch_cwv(page.url, strategy=strategy)
    
    # Add fetch timestamp
    cwv_data = metrics.to_dict()
    cwv_data["fetched_at"] = datetime.now(timezone.utc).isoformat()
    cwv_data["strategy"] = strategy
    
    # Cache in database
    page.cwv_data = cwv_data
    await db.commit()
    
    return {
        "page_id": str(page_id),
        "url": page.url,
        "cached": False,
        "cwv": cwv_data,
    }


@router.get("/url")
async def get_url_cwv(
    url: str = Query(..., description="URL to analyze"),
    strategy: str = Query("mobile", description="mobile or desktop"),
):
    """
    Get Core Web Vitals for any URL (not necessarily in database).
    """
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    metrics = await cwv_service.fetch_cwv(url, strategy=strategy)
    
    cwv_data = metrics.to_dict()
    cwv_data["fetched_at"] = datetime.now(timezone.utc).isoformat()
    cwv_data["strategy"] = strategy
    
    return {
        "url": url,
        "cwv": cwv_data,
    }


@router.get("/prompt/{prompt_id}")
async def get_prompt_matches_cwv(
    prompt_id: UUID,
    refresh: bool = Query(False, description="Force refresh from PageSpeed API"),
    strategy: str = Query("mobile", description="mobile or desktop"),
    limit: int = Query(2, ge=1, le=10, description="Max pages to fetch CWV for (PageSpeed API is slow)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Core Web Vitals for top matched pages of a prompt.
    Limited by default because PageSpeed API is slow (~30s per page).
    """
    from app.models.match import Match
    
    # Get matches for this prompt (limited)
    query = (
        select(Match, Page)
        .join(Page, Match.page_id == Page.id)
        .where(Match.prompt_id == prompt_id)
        .order_by(Match.similarity_score.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    matches = result.all()
    
    if not matches:
        return {
            "prompt_id": str(prompt_id),
            "matches": [],
            "message": "No matched pages found for this prompt",
        }
    
    results = []
    for match, page in matches:
        # Check for cached data first (skip if refresh is requested)
        cwv_data = None
        cached = False
        
        if not refresh and page.cwv_data:
            fetched_at = page.cwv_data.get("fetched_at")
            if fetched_at:
                try:
                    fetch_time = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                    age_hours = (datetime.now(timezone.utc) - fetch_time).total_seconds() / 3600
                    if age_hours < 24:
                        cwv_data = page.cwv_data
                        cached = True
                except (ValueError, TypeError):
                    pass
        
        # Fetch if not cached or refresh requested
        if not cwv_data:
            metrics = await cwv_service.fetch_cwv(page.url, strategy=strategy)
            cwv_data = metrics.to_dict()
            cwv_data["fetched_at"] = datetime.now(timezone.utc).isoformat()
            cwv_data["strategy"] = strategy
            
            # Cache in database
            page.cwv_data = cwv_data
        
        results.append({
            "page_id": str(page.id),
            "url": page.url,
            "title": page.title,
            "similarity_score": match.similarity_score,
            "cached": cached,
            "cwv": cwv_data,
        })
    
    await db.commit()
    
    return {
        "prompt_id": str(prompt_id),
        "matches": results,
    }


@router.get("/status")
async def get_cwv_status():
    """
    Check if CWV service is enabled and configured.
    """
    return {
        "enabled": cwv_service.enabled,
        "api_configured": bool(cwv_service.api_key),
        "message": (
            "CWV service is fully configured" if cwv_service.enabled 
            else "Google PageSpeed API key not configured. CWV will work but with rate limits."
        ),
    }



