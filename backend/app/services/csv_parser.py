"""CSV parsing and processing service."""

import os
import csv
import io
import math
import json
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import pandas as pd
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def sanitize_for_json(obj: Any) -> Any:
    """Recursively sanitize data to be JSON-serializable (handles NaN, Infinity, etc.)."""
    if obj is None:
        return None
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.floating, np.integer)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [sanitize_for_json(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(x) for x in obj]
    if pd.isna(obj):
        return None
    return obj


# Known column name variations for auto-mapping
COLUMN_MAPPINGS = {
    "prompt": ["prompt", "query", "question", "text", "search_query", "user_query"],
    "topic": ["topic", "subject", "theme", "group"],
    "category": ["category", "type", "classification", "section"],
    "region": ["region", "country", "location", "geo", "market"],
    "popularity": ["popularity", "volume", "search_volume", "traffic"],
    "sentiment": ["sentiment", "sentiment_score", "tone"],
    "visibility_score": ["visibility score", "visibility_score", "visibility", "score"],
    "sources_urls": ["sources urls", "source_urls", "sources", "urls", "source urls"],
    "source_types": ["sources content types", "source_types", "content_types", "source types"],
}


class CSVParserService:
    """Service for parsing and validating CSV files."""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def save_uploaded_file(self, filename: str, content: bytes) -> str:
        """Save uploaded file and return the path."""
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        file_path = os.path.join(self.upload_dir, f"{UUID(int=0).hex[:8]}_{safe_filename}")
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info("Saved uploaded CSV", filename=filename, path=file_path)
        return file_path
    
    def detect_delimiter(self, content: str) -> str:
        """Detect CSV delimiter."""
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(content[:4096])
            return dialect.delimiter
        except csv.Error:
            return ","
    
    def get_preview(
        self, 
        file_path: str, 
        num_rows: int = 10
    ) -> Tuple[List[str], List[Dict[str, Any]], int]:
        """
        Get CSV preview with columns, sample rows, and total count.
        
        Returns:
            Tuple of (columns, preview_rows, total_rows)
        """
        try:
            # Read with pandas for robust parsing
            df = pd.read_csv(file_path, nrows=num_rows + 1)
            
            columns = list(df.columns)
            preview_rows = []
            
            for idx, row in df.head(num_rows).iterrows():
                preview_rows.append({
                    "row_number": idx + 1,
                    "data": row.to_dict()
                })
            
            # Count total rows
            with open(file_path, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for _ in f) - 1  # Subtract header
            
            return columns, preview_rows, total_rows
            
        except Exception as e:
            logger.error("Failed to read CSV preview", error=str(e), path=file_path)
            raise ValueError(f"Failed to parse CSV: {str(e)}")
    
    def suggest_column_mapping(self, columns: List[str]) -> Dict[str, Optional[str]]:
        """Suggest column mappings based on column names."""
        mapping = {}
        columns_lower = {col.lower().strip(): col for col in columns}
        
        for target_field, variations in COLUMN_MAPPINGS.items():
            mapping[target_field] = None
            for variation in variations:
                if variation in columns_lower:
                    mapping[target_field] = columns_lower[variation]
                    break
        
        return mapping
    
    def parse_row(
        self, 
        row: Dict[str, Any], 
        column_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Parse a single CSV row using the column mapping."""
        result = {
            "raw_text": None,
            "topic": None,
            "region": None,
            "popularity_score": None,
            "sentiment_score": None,
            "visibility_score": None,
            "extra_data": {}
        }
        
        # Extract mapped fields
        if column_mapping.get("prompt"):
            result["raw_text"] = str(row.get(column_mapping["prompt"], "")).strip()
        
        if column_mapping.get("topic"):
            result["topic"] = str(row.get(column_mapping["topic"], "")).strip() or None
        
        if column_mapping.get("region"):
            result["region"] = str(row.get(column_mapping["region"], "")).strip() or None
        
        # Parse popularity (Low/Medium/High to 0-1)
        if column_mapping.get("popularity"):
            pop_value = str(row.get(column_mapping["popularity"], "")).strip().lower()
            result["popularity_score"] = self._parse_popularity(pop_value)
        
        # Parse sentiment
        if column_mapping.get("sentiment"):
            sent_value = str(row.get(column_mapping["sentiment"], "")).strip().lower()
            result["sentiment_score"] = self._parse_sentiment(sent_value)
        
        # Parse visibility score (percentage)
        if column_mapping.get("visibility_score"):
            vis_value = str(row.get(column_mapping["visibility_score"], "")).strip()
            result["visibility_score"] = self._parse_percentage(vis_value)
        
        # Store extra data
        if column_mapping.get("sources_urls"):
            urls_str = str(row.get(column_mapping["sources_urls"], "")).strip()
            result["extra_data"]["sources_urls"] = [u.strip() for u in urls_str.split(";") if u.strip()]
        
        if column_mapping.get("source_types"):
            types_str = str(row.get(column_mapping["source_types"], "")).strip()
            result["extra_data"]["source_types"] = [t.strip() for t in types_str.split(";") if t.strip()]
        
        # Store any unmapped columns in extra_data
        mapped_cols = set(v for v in column_mapping.values() if v)
        for col, value in row.items():
            if col not in mapped_cols:
                # Sanitize value for JSON compatibility
                sanitized = sanitize_for_json(value)
                if sanitized is not None and sanitized != "":
                    result["extra_data"][col] = sanitized
        
        # Final sanitization of extra_data
        result["extra_data"] = sanitize_for_json(result["extra_data"])
        
        return result
    
    def _parse_popularity(self, value: str) -> Optional[float]:
        """Parse popularity value to 0-1 scale."""
        if not value or value in ("n/a", ""):
            return None
        
        popularity_map = {
            "low": 0.33,
            "medium": 0.66,
            "high": 1.0,
        }
        
        if value in popularity_map:
            return popularity_map[value]
        
        # Try to parse as number
        try:
            return float(value) / 100 if float(value) > 1 else float(value)
        except ValueError:
            return None
    
    def _parse_sentiment(self, value: str) -> Optional[float]:
        """Parse sentiment value to -1 to 1 scale."""
        if not value or value in ("n/a", ""):
            return None
        
        sentiment_map = {
            "positive": 1.0,
            "neutral": 0.0,
            "negative": -1.0,
        }
        
        if value in sentiment_map:
            return sentiment_map[value]
        
        # Try to parse as number
        try:
            return float(value)
        except ValueError:
            return None
    
    def _parse_percentage(self, value: str) -> Optional[float]:
        """Parse percentage string to 0-1 float."""
        if not value or value in ("n/a", ""):
            return None
        
        try:
            # Remove % sign
            clean_value = value.replace("%", "").strip()
            return float(clean_value) / 100
        except ValueError:
            return None
    
    def iterate_rows(
        self, 
        file_path: str, 
        column_mapping: Dict[str, str],
        batch_size: int = 100
    ):
        """
        Generator that yields batches of parsed rows.
        
        Yields:
            List of parsed row dictionaries
        """
        df = pd.read_csv(file_path, chunksize=batch_size)
        
        for chunk in df:
            batch = []
            for _, row in chunk.iterrows():
                parsed = self.parse_row(row.to_dict(), column_mapping)
                if parsed["raw_text"]:  # Skip rows without prompt text
                    batch.append(parsed)
            
            if batch:
                yield batch


# Singleton instance
csv_parser = CSVParserService()

