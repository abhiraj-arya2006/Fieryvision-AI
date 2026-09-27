import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH)
load_dotenv(".env")

class Settings(BaseSettings):
    FIRMS_MAP_KEY: Optional[str] = os.getenv("FIRMS_MAP_KEY", "")
    FIRMS_DATA_SOURCE: str = os.getenv("FIRMS_DATA_SOURCE", "VIIRS_NOAA20_NRT")
    FIRMS_AREA: str = os.getenv("FIRMS_AREA", "WORLD")
    FIRMS_DAY_RANGE: int = int(os.getenv("FIRMS_DAY_RANGE", "1"))
    FIRMS_CACHE_FILE: str = os.path.join(_BACKEND_DIR, "data", "cache", "firms_cache.json")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Cache settings
    FIRMS_CACHE_TTL_SECONDS: int = 600  # 10 minutes cache for FIRMS
    WEATHER_CACHE_TTL_MINUTES: int = 30  # 30 minutes cache for Open-Meteo
    EMERGENCY_CACHE_TTL_HOURS: int = 24  # 24 hours cache for OSM Overpass
    OVERPASS_CACHE_TTL_HOURS: int = 24

    # Hotspot Intelligence Configuration
    HOTSPOT_GRID_KM: float = float(os.getenv("HOTSPOT_GRID_KM", "20.0"))
    HOTSPOT_MIN_DETECTIONS: int = int(os.getenv("HOTSPOT_MIN_DETECTIONS", "2"))
    HOTSPOT_TEMPORAL_WINDOW_HOURS: float = float(os.getenv("HOTSPOT_TEMPORAL_WINDOW_HOURS", "72.0"))
    OVERPASS_FACILITY_RADIUS_M: int = 5000
    
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
    
    # Database URL configuration
    DATABASE_URL: str = "sqlite:///./fieryvision.db"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
