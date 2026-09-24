"""
NASA FIRMS Active / Near-Real-Time Data Service.
Safely queries NASA FIRMS NRT API using FIRMS_MAP_KEY, protects API keys,
and normalizes real-time satellite observations.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List, Union
import logging
import pandas as pd

from data_processing.config import FIRMS_CONFIG, GEO_CONFIG
from data_processing.geo.filter import get_bounding_box_for_radius, filter_to_monitoring_area
from data_processing.firms.loader import load_and_normalize_firms, _create_empty_normalized_df

logger = logging.getLogger("fieryvision.firms.active_service")


class FIRMSActiveService:
    """
    Client for NASA FIRMS Near-Real-Time (NRT) API.
    Handles authentication, bounding-box queries, response normalization, and safe fallbacks.
    """

    def __init__(
        self,
        map_key: Optional[str] = None,
        base_url: str = FIRMS_CONFIG.BASE_API_URL,
        timeout: float = FIRMS_CONFIG.REQUEST_TIMEOUT_SECONDS,
    ):
        # Retrieve key securely from parameter or environment
        self._map_key = map_key or os.environ.get(FIRMS_CONFIG.ENV_MAP_KEY_NAME)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def has_api_key(self) -> bool:
        """Indicate whether an API key is available without exposing it."""
        return bool(self._map_key and self._map_key.strip())

    def __repr__(self) -> str:
        return f"<FIRMSActiveService has_api_key={self.has_api_key}>"

    def fetch_area(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        days: int = FIRMS_CONFIG.DEFAULT_ACTIVE_DAYS,
        products: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Query FIRMS Area API for a rectangular bounding box.
        
        Returns:
            Tuple of (normalized_observations_df, metadata_dict).
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        target_products = products or list(FIRMS_CONFIG.DEFAULT_PRODUCTS)

        if not self.has_api_key:
            logger.info("NASA FIRMS API key not configured (%s missing).", FIRMS_CONFIG.ENV_MAP_KEY_NAME)
            return _create_empty_normalized_df(), {
                "status": "unavailable",
                "source_mode": "none",
                "fetch_timestamp": timestamp,
                "record_count": 0,
                "message": f"Environment variable {FIRMS_CONFIG.ENV_MAP_KEY_NAME} is not set. Real-time satellite query skipped.",
            }

        # Area coordinate string format: W,S,E,N
        area_str = f"{min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}"
        all_dfs: List[pd.DataFrame] = []
        errors: List[str] = []

        for prod in target_products:
            # FIRMS Area API format: /api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDS]/[DAYS]
            url = f"{self.base_url}/area/csv/{self._map_key}/{prod}/{area_str}/{days}"
            try:
                import httpx
                response = httpx.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    text = response.text.strip()
                    # Check if FIRMS returned an error message instead of CSV
                    if text.startswith("Invalid") or "not found" in text.lower() or "error" in text.lower():
                        logger.warning("NASA FIRMS returned notice for product %s", prod)
                        errors.append(f"{prod}: {text[:80]}")
                        continue
                    df_prod = load_and_normalize_firms(text)
                    if not df_prod.empty:
                        all_dfs.append(df_prod)
                else:
                    errors.append(f"{prod}: HTTP {response.status_code}")
            except Exception as exc:
                # Never log the URL with the map key
                safe_err = type(exc).__name__
                logger.warning("Failed querying product %s: %s", prod, safe_err)
                errors.append(f"{prod}: {safe_err}")

        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            combined_df = combined_df.drop_duplicates(
                subset=["latitude", "longitude", "acq_date", "acq_time", "satellite"]
            ).reset_index(drop=True)
            return combined_df, {
                "status": "active",
                "source_mode": "nasa_firms_nrt_api",
                "fetch_timestamp": timestamp,
                "record_count": len(combined_df),
                "products_queried": target_products,
                "errors": errors if errors else None,
            }

        return _create_empty_normalized_df(), {
            "status": "empty_or_failed",
            "source_mode": "nasa_firms_nrt_api",
            "fetch_timestamp": timestamp,
            "record_count": 0,
            "products_queried": target_products,
            "errors": errors if errors else None,
        }

    def fetch_for_giaspura(
        self,
        radius_km: float = GEO_CONFIG.DEFAULT_MONITORING_RADIUS_KM,
        days: int = FIRMS_CONFIG.DEFAULT_ACTIVE_DAYS,
        products: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetch active FIRMS thermal anomalies for the Giaspura regional monitoring area.
        Bbox query followed by precise metric radial distance filtering.
        """
        min_lat, min_lon, max_lat, max_lon = get_bounding_box_for_radius(
            center_lat=GEO_CONFIG.GIASPURA_LATITUDE,
            center_lon=GEO_CONFIG.GIASPURA_LONGITUDE,
            radius_km=radius_km,
        )

        df_raw, meta = self.fetch_area(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            days=days,
            products=products,
        )

        if df_raw.empty:
            return df_raw, meta

        # Filter strictly to circular monitoring area
        df_filtered = filter_to_monitoring_area(
            df_raw,
            center_lat=GEO_CONFIG.GIASPURA_LATITUDE,
            center_lon=GEO_CONFIG.GIASPURA_LONGITUDE,
            radius_km=radius_km,
        )
        meta["record_count_after_filter"] = len(df_filtered)
        meta["radius_km"] = radius_km
        return df_filtered, meta
