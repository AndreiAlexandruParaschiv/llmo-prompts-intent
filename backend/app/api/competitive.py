"""Competitive Analysis API endpoints."""

import asyncio
import httpx
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.config import settings
from app.models.prompt import Prompt, MatchStatus
from app.models.match import Match
from app.models.page import Page
from app.models.csv_import import CSVImport
from app.services.azure_openai import azure_openai_service

logger = get_logger(__name__)
router = APIRouter()


async def search_competitors(query: str, our_domain: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for competitor content using multiple search approaches.
    Returns list of {url, title, snippet} excluding our domain.
    """
    results = []
    
    # Try multiple search methods
    search_methods = [
        _search_via_duckduckgo_api,
        _search_via_duckduckgo_html,
        _search_via_bing,
    ]
    
    for search_method in search_methods:
        try:
            results = await search_method(query, our_domain, num_results)
            if results:
                logger.info(f"Search successful via {search_method.__name__}: {len(results)} results")
                break
        except Exception as e:
            logger.warning(f"Search method {search_method.__name__} failed: {e}")
            continue
    
    return results


async def _search_via_duckduckgo_api(query: str, our_domain: str, num_results: int) -> List[Dict[str, str]]:
    """Search using DuckDuckGo Instant Answer API."""
    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            follow_redirects=True
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Get related topics
            for topic in data.get("RelatedTopics", [])[:num_results * 2]:
                if isinstance(topic, dict) and "FirstURL" in topic:
                    url = topic.get("FirstURL", "")
                    if our_domain and our_domain.lower() in url.lower():
                        continue
                    if not url.startswith("http"):
                        continue
                    results.append({
                        "url": url,
                        "title": topic.get("Text", "")[:100],
                        "snippet": topic.get("Text", "")
                    })
                    if len(results) >= num_results:
                        break
    
    return results


async def _search_via_duckduckgo_html(query: str, our_domain: str, num_results: int) -> List[Dict[str, str]]:
    """Search using DuckDuckGo HTML interface."""
    results = []
    from bs4 import BeautifulSoup
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
            follow_redirects=True
        )
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors
            for result in soup.select('.result, .web-result, .results_links'):
                link = result.select_one('a.result__a, a.result__url, a[href]')
                snippet = result.select_one('.result__snippet, .result__body, .snippet')
                title_elem = result.select_one('.result__title, h2, h3')
                
                if link:
                    url = link.get('href', '')
                    
                    # DuckDuckGo redirects - extract actual URL
                    if 'uddg=' in url:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                        url = parsed.get('uddg', [url])[0]
                    
                    title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
                    
                    if our_domain and our_domain.lower() in url.lower():
                        continue
                    if not url.startswith('http'):
                        continue
                    
                    results.append({
                        "url": url,
                        "title": title,
                        "snippet": snippet.get_text(strip=True) if snippet else ""
                    })
                    
                    if len(results) >= num_results:
                        break
    
    return results


async def _search_via_bing(query: str, our_domain: str, num_results: int) -> List[Dict[str, str]]:
    """Search using Bing HTML interface."""
    results = []
    from bs4 import BeautifulSoup
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
            follow_redirects=True
        )
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for result in soup.select('.b_algo, li.b_algo'):
                link = result.select_one('h2 a, a')
                snippet = result.select_one('.b_caption p, p')
                
                if link:
                    url = link.get('href', '')
                    title = link.get_text(strip=True)
                    
                    if our_domain and our_domain.lower() in url.lower():
                        continue
                    if not url.startswith('http'):
                        continue
                    
                    results.append({
                        "url": url,
                        "title": title,
                        "snippet": snippet.get_text(strip=True) if snippet else ""
                    })
                    
                    if len(results) >= num_results:
                        break
    
    return results


@router.get("/high-intent-prompts", response_model=dict)
async def get_high_intent_prompts(
    project_id: UUID = Query(...),
    min_transaction_score: float = Query(0.5, description="Minimum transaction score (0-1)"),
    match_status: str = Query("answered", description="Filter by match status: answered, partial, all"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get high transaction-intent prompts that are answered (have matching content).
    These are opportunities to analyze against competitors.
    """
    # Get CSV imports for this project
    imports_query = select(CSVImport.id).where(CSVImport.project_id == project_id)
    imports_result = await db.execute(imports_query)
    import_ids = [row[0] for row in imports_result.fetchall()]
    
    if not import_ids:
        return {"prompts": [], "total": 0, "page": page, "page_size": page_size, "topic": topic}
    
    # Build query for high-intent prompts
    query = (
        select(Prompt)
        .where(
            Prompt.csv_import_id.in_(import_ids),
            Prompt.transaction_score >= min_transaction_score
        )
    )
    
    # Filter by topic
    if topic:
        query = query.where(Prompt.topic == topic)
    
    # Filter by match status
    if match_status == "answered":
        query = query.where(Prompt.match_status == MatchStatus.ANSWERED)
    elif match_status == "partial":
        query = query.where(Prompt.match_status == MatchStatus.PARTIAL)
    elif match_status != "all":
        query = query.where(Prompt.match_status.in_([MatchStatus.ANSWERED, MatchStatus.PARTIAL]))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Get paginated results, ordered by transaction score
    query = query.order_by(Prompt.transaction_score.desc(), Prompt.popularity_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    prompts = result.scalars().all()
    
    # Get matches for each prompt
    prompt_data = []
    for prompt in prompts:
        # Get best match
        match_query = (
            select(Match, Page)
            .join(Page, Match.page_id == Page.id)
            .where(Match.prompt_id == prompt.id)
            .order_by(Match.similarity_score.desc())
            .limit(1)
        )
        match_result = await db.execute(match_query)
        match_row = match_result.first()
        
        best_match = None
        if match_row:
            match_obj, page_obj = match_row
            best_match = {
                "url": page_obj.url,
                "title": page_obj.title,
                "snippet": match_obj.matched_snippet or page_obj.meta_description,
                "score": match_obj.similarity_score
            }
        
        prompt_data.append({
            "id": str(prompt.id),
            "text": prompt.raw_text,
            "topic": prompt.topic,
            "transaction_score": prompt.transaction_score,
            "popularity_score": prompt.popularity_score,
            "intent_label": prompt.intent_label.value if prompt.intent_label else None,
            "match_status": prompt.match_status.value if prompt.match_status else None,
            "best_match_score": prompt.best_match_score,
            "best_match": best_match
        })
    
    return {
        "prompts": prompt_data,
        "total": total or 0,
        "page": page,
        "page_size": page_size
    }


@router.post("/analyze/{prompt_id}", response_model=dict)
async def analyze_competitive_position(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze competitive position for a specific high-intent prompt.
    Searches for competitor content and provides AI recommendations.
    """
    # Get the prompt
    prompt = await db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Get best matching page
    match_query = (
        select(Match, Page)
        .join(Page, Match.page_id == Page.id)
        .where(Match.prompt_id == prompt_id)
        .order_by(Match.similarity_score.desc())
        .limit(1)
    )
    match_result = await db.execute(match_query)
    match_row = match_result.first()
    
    if not match_row:
        raise HTTPException(status_code=400, detail="No matching content found for this prompt")
    
    match_obj, page_obj = match_row
    
    # Extract our domain from the page URL
    from urllib.parse import urlparse
    our_domain = urlparse(page_obj.url).netloc
    
    # Search for competitors
    competitor_results = await search_competitors(
        query=prompt.raw_text,
        our_domain=our_domain,
        num_results=5
    )
    
    # Prepare our content info
    our_content = {
        "url": page_obj.url,
        "title": page_obj.title or "",
        "snippet": match_obj.matched_snippet or page_obj.meta_description or page_obj.content[:500] if page_obj.content else ""
    }
    
    # Get AI analysis if available
    ai_analysis = None
    if azure_openai_service.enabled and competitor_results:
        ai_analysis = azure_openai_service.analyze_competitive_position(
            prompt_text=prompt.raw_text,
            transaction_score=prompt.transaction_score or 0,
            our_content=our_content,
            competitor_results=competitor_results
        )
    
    return {
        "prompt_id": str(prompt_id),
        "prompt_text": prompt.raw_text,
        "transaction_score": prompt.transaction_score,
        "intent_label": prompt.intent_label.value if prompt.intent_label else None,
        "our_content": our_content,
        "match_score": match_obj.similarity_score,
        "competitors": competitor_results,
        "ai_analysis": ai_analysis,
        "ai_enabled": azure_openai_service.enabled,
    }


@router.get("/summary", response_model=dict)
async def get_competitive_summary(
    project_id: UUID = Query(...),
    min_transaction_score: float = Query(0.5),
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary statistics for competitive analysis opportunities.
    """
    # Get CSV imports for this project
    imports_query = select(CSVImport.id).where(CSVImport.project_id == project_id)
    imports_result = await db.execute(imports_query)
    import_ids = [row[0] for row in imports_result.fetchall()]
    
    if not import_ids:
        return {
            "total_high_intent": 0,
            "answered_high_intent": 0,
            "partial_high_intent": 0,
            "avg_transaction_score": 0,
            "top_topics": []
        }
    
    # Count high-intent prompts
    total_query = select(func.count()).select_from(Prompt).where(
        Prompt.csv_import_id.in_(import_ids),
        Prompt.transaction_score >= min_transaction_score
    )
    total_high_intent = await db.scalar(total_query) or 0
    
    # Count answered high-intent
    answered_query = select(func.count()).select_from(Prompt).where(
        Prompt.csv_import_id.in_(import_ids),
        Prompt.transaction_score >= min_transaction_score,
        Prompt.match_status == MatchStatus.ANSWERED
    )
    answered_high_intent = await db.scalar(answered_query) or 0
    
    # Count partial high-intent
    partial_query = select(func.count()).select_from(Prompt).where(
        Prompt.csv_import_id.in_(import_ids),
        Prompt.transaction_score >= min_transaction_score,
        Prompt.match_status == MatchStatus.PARTIAL
    )
    partial_high_intent = await db.scalar(partial_query) or 0
    
    # Average transaction score for high-intent
    avg_query = select(func.avg(Prompt.transaction_score)).where(
        Prompt.csv_import_id.in_(import_ids),
        Prompt.transaction_score >= min_transaction_score
    )
    avg_transaction_score = await db.scalar(avg_query) or 0
    
    # Top topics for high-intent prompts
    topics_query = (
        select(Prompt.topic, func.count().label('count'))
        .where(
            Prompt.csv_import_id.in_(import_ids),
            Prompt.transaction_score >= min_transaction_score,
            Prompt.topic.isnot(None)
        )
        .group_by(Prompt.topic)
        .order_by(func.count().desc())
        .limit(5)
    )
    topics_result = await db.execute(topics_query)
    top_topics = [{"topic": row[0], "count": row[1]} for row in topics_result.fetchall()]
    
    return {
        "total_high_intent": total_high_intent,
        "answered_high_intent": answered_high_intent,
        "partial_high_intent": partial_high_intent,
        "avg_transaction_score": round(avg_transaction_score, 2) if avg_transaction_score else 0,
        "top_topics": top_topics
    }

