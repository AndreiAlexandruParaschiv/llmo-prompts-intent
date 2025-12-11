"""Application configuration settings."""

from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "LLMO Prompts Intent Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://llmo:llmo_dev_password@localhost:5432/llmo_prompts"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # File storage
    UPLOAD_DIR: str = "./uploads"
    SNAPSHOTS_DIR: str = "./snapshots"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # NLP Settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # Intent Classification
    TRANSACTIONAL_THRESHOLD: float = 0.6
    MATCH_THRESHOLD_ANSWERED: float = 0.75
    MATCH_THRESHOLD_PARTIAL: float = 0.50
    
    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # Crawler settings
    CRAWLER_MAX_PAGES: int = 100
    CRAWLER_RATE_LIMIT: float = 1.0  # seconds between requests
    CRAWLER_TIMEOUT: int = 30000  # milliseconds
    CRAWLER_RESPECT_ROBOTS: bool = True
    
    # JWT Settings
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

