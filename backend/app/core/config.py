import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    FIRMS_MAP_KEY: Optional[str] = os.getenv("FIRMS_MAP_KEY", "")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Target Area: Giaspura, Ludhiana, Punjab, India
    GIASPURA_LAT: float = 30.875625
    GIASPURA_LON: float = 75.898481
    GIASPURA_RADIUS_KM: float = 15.0  # Regional monitoring buffer radius
    
    # Cache settings
    FIRMS_CACHE_TTL_SECONDS: int = 600  # 10 minutes cache for FIRMS
    
    # Database URL
    DATABASE_URL: str = "sqlite:///./fieryvision.db"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
