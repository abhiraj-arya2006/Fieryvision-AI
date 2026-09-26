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
    WEATHER_CACHE_TTL_MINUTES: int = 30  # 30 minutes cache for Open-Meteo
    EMERGENCY_CACHE_TTL_HOURS: int = 24  # 24 hours cache for OSM Overpass
    
    # Weather & Plume Configuration
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    WEATHER_REQUEST_TIMEOUT: int = 8
    PLUME_HORIZONS_HOURS: list[int] = [1, 3, 6, 12]
    PLUME_BASE_SPREAD_ANGLE: float = 30.0  # Base cone expansion in degrees
    PLUME_UNCERTAINTY_GROWTH_PER_HOUR: float = 2.5  # Angular uncertainty growth per hour
    PLUME_SPEED_DAMPENING_FACTOR: float = 0.85  # Atmospheric surface drag factor for dispersion screening
    
    # Emergency Infrastructure & Evacuation Buffers
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_REQUEST_TIMEOUT: int = 10
    EMERGENCY_QUERY_RADIUS_KM: float = 12.0
    BUFFER_1KM_M: float = 1000.0
    BUFFER_3KM_M: float = 3000.0
    
    # Database URL
    DATABASE_URL: str = "sqlite:///./fieryvision.db"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
