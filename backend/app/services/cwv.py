"""Core Web Vitals (CWV) service using Google PageSpeed Insights API."""

import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@dataclass
class CWVMetrics:
    """Core Web Vitals metrics."""
    # Core Web Vitals
    lcp: Optional[float] = None  # Largest Contentful Paint (ms)
    lcp_score: Optional[str] = None  # "good", "needs-improvement", "poor"
    fid: Optional[float] = None  # First Input Delay (ms) - deprecated, replaced by INP
    fid_score: Optional[str] = None
    inp: Optional[float] = None  # Interaction to Next Paint (ms)
    inp_score: Optional[str] = None
    cls: Optional[float] = None  # Cumulative Layout Shift (unitless)
    cls_score: Optional[str] = None
    
    # Additional metrics
    fcp: Optional[float] = None  # First Contentful Paint (ms)
    fcp_score: Optional[str] = None
    ttfb: Optional[float] = None  # Time to First Byte (ms)
    ttfb_score: Optional[str] = None
    
    # Overall scores
    performance_score: Optional[int] = None  # 0-100
    
    # Origin summary (field data from Chrome UX Report)
    has_field_data: bool = False
    
    # Error info
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lcp": self.lcp,
            "lcp_score": self.lcp_score,
            "fid": self.fid,
            "fid_score": self.fid_score,
            "inp": self.inp,
            "inp_score": self.inp_score,
            "cls": self.cls,
            "cls_score": self.cls_score,
            "fcp": self.fcp,
            "fcp_score": self.fcp_score,
            "ttfb": self.ttfb,
            "ttfb_score": self.ttfb_score,
            "performance_score": self.performance_score,
            "has_field_data": self.has_field_data,
            "error": self.error,
        }


class CWVService:
    """Service for fetching Core Web Vitals using Google PageSpeed Insights API."""
    
    PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    # CWV thresholds (in ms for timing metrics)
    THRESHOLDS = {
        "lcp": {"good": 2500, "poor": 4000},  # ms
        "fid": {"good": 100, "poor": 300},  # ms
        "inp": {"good": 200, "poor": 500},  # ms
        "cls": {"good": 0.1, "poor": 0.25},  # unitless
        "fcp": {"good": 1800, "poor": 3000},  # ms
        "ttfb": {"good": 800, "poor": 1800},  # ms
    }
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_PAGESPEED_API_KEY', None)
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("Google PageSpeed API key not configured. CWV fetching will be limited.")
    
    def _score_metric(self, metric_name: str, value: Optional[float]) -> Optional[str]:
        """Score a metric as good/needs-improvement/poor based on thresholds."""
        if value is None or metric_name not in self.THRESHOLDS:
            return None
        
        thresholds = self.THRESHOLDS[metric_name]
        if value <= thresholds["good"]:
            return "good"
        elif value <= thresholds["poor"]:
            return "needs-improvement"
        else:
            return "poor"
    
    async def fetch_cwv(self, url: str, strategy: str = "mobile") -> CWVMetrics:
        """
        Fetch Core Web Vitals for a URL using PageSpeed Insights API.
        
        Args:
            url: The URL to analyze
            strategy: "mobile" or "desktop"
            
        Returns:
            CWVMetrics with the results
        """
        metrics = CWVMetrics()
        
        try:
            params = {
                "url": url,
                "strategy": strategy,
                "category": "performance",
            }
            
            if self.api_key:
                params["key"] = self.api_key
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.PAGESPEED_API_URL, params=params)
                
                if response.status_code == 429:
                    metrics.error = "Rate limit exceeded. Please try again later."
                    return metrics
                
                if response.status_code != 200:
                    metrics.error = f"API error: {response.status_code}"
                    logger.warning(f"PageSpeed API error for {url}: {response.status_code}")
                    return metrics
                
                data = response.json()
                
                # Extract lab data (Lighthouse)
                lighthouse_result = data.get("lighthouseResult", {})
                audits = lighthouse_result.get("audits", {})
                
                # Performance score
                categories = lighthouse_result.get("categories", {})
                perf_category = categories.get("performance", {})
                if perf_category.get("score") is not None:
                    metrics.performance_score = int(perf_category["score"] * 100)
                
                # LCP
                lcp_audit = audits.get("largest-contentful-paint", {})
                if lcp_audit.get("numericValue") is not None:
                    metrics.lcp = round(lcp_audit["numericValue"], 0)
                    metrics.lcp_score = self._score_metric("lcp", metrics.lcp)
                
                # FCP
                fcp_audit = audits.get("first-contentful-paint", {})
                if fcp_audit.get("numericValue") is not None:
                    metrics.fcp = round(fcp_audit["numericValue"], 0)
                    metrics.fcp_score = self._score_metric("fcp", metrics.fcp)
                
                # CLS
                cls_audit = audits.get("cumulative-layout-shift", {})
                if cls_audit.get("numericValue") is not None:
                    metrics.cls = round(cls_audit["numericValue"], 3)
                    metrics.cls_score = self._score_metric("cls", metrics.cls)
                
                # TBT (Total Blocking Time) - proxy for INP in lab data
                tbt_audit = audits.get("total-blocking-time", {})
                
                # TTFB
                ttfb_audit = audits.get("server-response-time", {})
                if ttfb_audit.get("numericValue") is not None:
                    metrics.ttfb = round(ttfb_audit["numericValue"], 0)
                    metrics.ttfb_score = self._score_metric("ttfb", metrics.ttfb)
                
                # Extract field data (Chrome UX Report) if available
                loading_experience = data.get("loadingExperience", {})
                origin_experience = data.get("originLoadingExperience", {})
                
                field_metrics = loading_experience.get("metrics", {}) or origin_experience.get("metrics", {})
                
                if field_metrics:
                    metrics.has_field_data = True
                    
                    # Field LCP
                    field_lcp = field_metrics.get("LARGEST_CONTENTFUL_PAINT_MS", {})
                    if field_lcp.get("percentile"):
                        metrics.lcp = field_lcp["percentile"]
                        metrics.lcp_score = field_lcp.get("category", "").lower().replace("_", "-")
                    
                    # Field FID
                    field_fid = field_metrics.get("FIRST_INPUT_DELAY_MS", {})
                    if field_fid.get("percentile"):
                        metrics.fid = field_fid["percentile"]
                        metrics.fid_score = field_fid.get("category", "").lower().replace("_", "-")
                    
                    # Field INP
                    field_inp = field_metrics.get("INTERACTION_TO_NEXT_PAINT", {})
                    if field_inp.get("percentile"):
                        metrics.inp = field_inp["percentile"]
                        metrics.inp_score = field_inp.get("category", "").lower().replace("_", "-")
                    
                    # Field CLS
                    field_cls = field_metrics.get("CUMULATIVE_LAYOUT_SHIFT_SCORE", {})
                    if field_cls.get("percentile"):
                        metrics.cls = field_cls["percentile"] / 100  # Convert from score to decimal
                        metrics.cls_score = field_cls.get("category", "").lower().replace("_", "-")
                
                logger.info(f"CWV fetched for {url}: LCP={metrics.lcp}ms, CLS={metrics.cls}, Score={metrics.performance_score}")
                
        except httpx.TimeoutException:
            metrics.error = "Request timed out. The page may be slow to respond."
            logger.warning(f"CWV fetch timeout for {url}")
        except Exception as e:
            metrics.error = f"Failed to fetch CWV: {str(e)}"
            logger.error(f"CWV fetch error for {url}: {e}")
        
        return metrics
    
    def calculate_assessment(self, cwv_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate CWV assessment (pass/fail) based on Core Web Vitals metrics.
        
        A page passes if ALL three core metrics are "good":
        - LCP ≤ 2500ms
        - INP ≤ 200ms (or FID ≤ 100ms if INP not available)
        - CLS ≤ 0.1
        
        Args:
            cwv_data: The cached CWV data from the page
            
        Returns:
            Assessment dict with status, scores, and individual metric status
        """
        if not cwv_data:
            return {
                "status": "unknown",
                "performance_score": None,
                "has_data": False,
                "message": "CWV not analyzed yet",
                "lcp_ok": None,
                "inp_ok": None,
                "cls_ok": None,
            }
        
        # Get mobile data preferentially
        data = cwv_data.get("mobile", {}) or cwv_data
        
        if data.get("error"):
            return {
                "status": "unknown",
                "performance_score": None,
                "has_data": False,
                "message": data.get("error"),
                "lcp_ok": None,
                "inp_ok": None,
                "cls_ok": None,
            }
        
        # Extract metrics
        lcp = data.get("lcp")
        inp = data.get("inp")
        fid = data.get("fid")
        cls = data.get("cls")
        performance_score = data.get("performance_score")
        
        # Check individual metrics against thresholds
        lcp_ok = lcp is not None and lcp <= self.THRESHOLDS["lcp"]["good"]
        
        # Use INP preferentially, fall back to FID
        if inp is not None:
            inp_ok = inp <= self.THRESHOLDS["inp"]["good"]
        elif fid is not None:
            inp_ok = fid <= self.THRESHOLDS["fid"]["good"]
        else:
            inp_ok = None  # Unknown
        
        cls_ok = cls is not None and cls <= self.THRESHOLDS["cls"]["good"]
        
        # Determine overall pass/fail
        # A page passes only if ALL core metrics are good
        if lcp_ok is None and inp_ok is None and cls_ok is None:
            status = "unknown"
            message = "No CWV metrics available"
        elif lcp_ok and inp_ok and cls_ok:
            status = "passed"
            message = "All Core Web Vitals passed"
        elif lcp_ok is False or inp_ok is False or cls_ok is False:
            status = "failed"
            # Build failure message
            failures = []
            if lcp_ok is False:
                failures.append(f"LCP: {lcp}ms")
            if inp_ok is False:
                failures.append(f"INP: {inp}ms" if inp else f"FID: {fid}ms")
            if cls_ok is False:
                failures.append(f"CLS: {cls}")
            message = f"Failed: {', '.join(failures)}"
        else:
            # Some metrics unknown, some passing
            status = "partial"
            message = "Some metrics unavailable"
        
        return {
            "status": status,
            "performance_score": performance_score,
            "has_data": True,
            "message": message,
            "lcp_ok": lcp_ok,
            "inp_ok": inp_ok,
            "cls_ok": cls_ok,
        }


# Singleton instance
cwv_service = CWVService()

