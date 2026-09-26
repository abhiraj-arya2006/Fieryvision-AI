"""Open-Meteo weather service and screening-level plume transport engine.

Provides:
- Open-Meteo API integration with grid-quantized spatial caching (30 min TTL)
- Wind vector normalization (speed km/h, direction degrees, cardinal, downwind bearing)
- Time-aware multi-horizon screening plume cones (1h, 3h, 6h, 12h) with variable hourly wind shift curves
- Resilient fallback for offline / rate-limited operation
"""

import math
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.schemas.hotspot import (
    WindDataSchema,
    HourlyWindForecast,
    PlumeHorizonFeature,
    PlumeConeResponse
)

logger = logging.getLogger("fieryvision.weather")

EARTH_RADIUS_KM = 6371.0

CARDINAL_DIRECTIONS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
]


def degrees_to_cardinal(deg: float) -> str:
    """Convert meteorological wind direction in degrees to 16-point cardinal compass."""
    val = int((deg / 22.5) + 0.5)
    return CARDINAL_DIRECTIONS[val % 16]


def destination_point(lat: float, lon: float, bearing_deg: float, distance_km: float) -> Tuple[float, float]:
    """
    Calculate destination point latitude and longitude given starting coordinates,
    initial bearing (degrees clockwise from North), and distance (km) on spherical Earth.
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)
    d_over_r = distance_km / EARTH_RADIUS_KM

    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(d_over_r) +
        math.cos(lat_rad) * math.sin(d_over_r) * math.cos(bearing_rad)
    )
    lon2 = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(d_over_r) * math.cos(lat_rad),
        math.cos(d_over_r) - math.sin(lat_rad) * math.sin(lat2)
    )

    return math.degrees(lat2), math.degrees(lon2)


class WeatherCache:
    """In-memory grid-quantized cache for weather responses."""

    def __init__(self, ttl_minutes: int = 30):
        self.ttl_seconds = ttl_minutes * 60
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def _grid_key(self, lat: float, lon: float) -> str:
        # Quantize to ~11km grid (0.1 degree)
        return f"{round(lat, 1):.1f}_{round(lon, 1):.1f}"

    def get(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        key = self._grid_key(lat, lon)
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return data
            else:
                del self._cache[key]
        return None

    def set(self, lat: float, lon: float, data: Dict[str, Any]):
        key = self._grid_key(lat, lon)
        self._cache[key] = (time.time(), data)


weather_cache = WeatherCache(ttl_minutes=settings.WEATHER_CACHE_TTL_MINUTES)


class WeatherService:
    """Client for retrieving real-time meteorological conditions and wind forecasts."""

    async def get_wind_data(self, lat: float, lon: float) -> WindDataSchema:
        """Fetch current wind speed, direction, and hourly forecasts from Open-Meteo with caching."""
        cached = weather_cache.get(lat, lon)
        if cached:
            cached_schema = WindDataSchema(**cached)
            cached_schema.is_cached = True
            return cached_schema

        try:
            params = {
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
                "hourly": "wind_speed_10m,wind_direction_10m",
                "forecast_days": 1,
                "wind_speed_unit": "kmh"
            }

            async with httpx.AsyncClient(timeout=settings.WEATHER_REQUEST_TIMEOUT) as client:
                response = await client.get(settings.OPEN_METEO_BASE_URL, params=params)
                
                if response.status_code == 200:
                    raw = response.json()
                    current = raw.get("current", {})
                    hourly = raw.get("hourly", {})

                    wind_speed = float(current.get("wind_speed_10m", 15.0))
                    wind_dir = float(current.get("wind_direction_10m", 270.0))
                    downwind = (wind_dir + 180.0) % 360.0
                    temp = current.get("temperature_2m")
                    humidity = current.get("relative_humidity_2m")

                    hourly_forecasts: List[HourlyWindForecast] = []
                    times = hourly.get("time", [])
                    speeds = hourly.get("wind_speed_10m", [])
                    dirs = hourly.get("wind_direction_10m", [])

                    for offset in range(min(12, len(times))):
                        spd = float(speeds[offset]) if offset < len(speeds) else wind_speed
                        dr = float(dirs[offset]) if offset < len(dirs) else wind_dir
                        dw = (dr + 180.0) % 360.0
                        hourly_forecasts.append(HourlyWindForecast(
                            hour_offset=offset + 1,
                            time=times[offset] if offset < len(times) else f"+{offset+1}h",
                            wind_speed_kmh=round(spd, 1),
                            wind_direction_deg=round(dr, 1),
                            downwind_bearing_deg=round(dw, 1),
                            cardinal=degrees_to_cardinal(dr)
                        ))

                    wind_data = WindDataSchema(
                        latitude=lat,
                        longitude=lon,
                        wind_speed_kmh=round(wind_speed, 1),
                        wind_direction_deg=round(wind_dir, 1),
                        downwind_bearing_deg=round(downwind, 1),
                        cardinal_direction=degrees_to_cardinal(wind_dir),
                        temperature_c=round(float(temp), 1) if temp is not None else None,
                        humidity_percent=round(float(humidity), 1) if humidity is not None else None,
                        hourly_forecast=hourly_forecasts,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source="Open-Meteo",
                        is_cached=False,
                        attribution="Weather data provided by Open-Meteo under CC BY 4.0 license"
                    )

                    weather_cache.set(lat, lon, wind_data.model_dump())
                    return wind_data
                else:
                    logger.warning("Open-Meteo returned status %d: %s. Using atmospheric fallback.", response.status_code, response.text)
        except Exception as exc:
            logger.warning("Failed to reach Open-Meteo API: %s. Using atmospheric fallback.", exc)

        # Realistic atmospheric baseline fallback (e.g. westerly 18 km/h)
        return self._generate_fallback_wind(lat, lon)

    def _generate_fallback_wind(self, lat: float, lon: float) -> WindDataSchema:
        """Generate physically consistent meteorological estimate when Open-Meteo is unreachable."""
        # Determinstic baseline based on latitude bands (Hadley cell / Ferrel westerlies)
        if abs(lat) < 23.5:
            base_dir = 75.0 if lat > 0 else 105.0  # Trade winds (Easterlies)
            base_spd = 14.0
        else:
            base_dir = 260.0  # Prevailing westerlies
            base_spd = 18.5

        downwind = (base_dir + 180.0) % 360.0

        hourly: List[HourlyWindForecast] = []
        for h in range(1, 13):
            shift = math.sin(h * 0.4) * 8.0
            spd = max(5.0, base_spd + math.cos(h * 0.5) * 4.0)
            dr = (base_dir + shift) % 360.0
            dw = (dr + 180.0) % 360.0
            hourly.append(HourlyWindForecast(
                hour_offset=h,
                time=f"+{h}h",
                wind_speed_kmh=round(spd, 1),
                wind_direction_deg=round(dr, 1),
                downwind_bearing_deg=round(dw, 1),
                cardinal=degrees_to_cardinal(dr)
            ))

        return WindDataSchema(
            latitude=lat,
            longitude=lon,
            wind_speed_kmh=base_spd,
            wind_direction_deg=base_dir,
            downwind_bearing_deg=downwind,
            cardinal_direction=degrees_to_cardinal(base_dir),
            temperature_c=28.5,
            humidity_percent=42.0,
            hourly_forecast=hourly,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="FieryVision Atmospheric Baseline Model (Open-Meteo Offline)",
            is_cached=False,
            attribution="Screening meteorological estimate generated offline"
        )


class PlumeEngine:
    """
    Computes time-aware indicative downwind transport cones and exposure polygons
    based on atmospheric wind speed, direction, and hourly directional variability.
    """

    def generate_plume_cones(
        self,
        hotspot_id: str,
        hotspot_name: str,
        lat: float,
        lon: float,
        wind: WindDataSchema
    ) -> PlumeConeResponse:
        """
        Generate 1h, 3h, 6h, 12h downwind transport polygons with variable wind curvature.
        """
        horizons_features: List[PlumeHorizonFeature] = []

        # Build hourly path centerline points taking into account changing forecast winds
        hourly_forecasts = wind.hourly_forecast
        current_speed = wind.wind_speed_kmh
        current_bearing = wind.downwind_bearing_deg

        for horizon_hours in settings.PLUME_HORIZONS_HOURS:
            # 1. Calculate cumulative transport distance with surface drag reduction
            effective_speed = current_speed * settings.PLUME_SPEED_DAMPENING_FACTOR
            distance_km = round(effective_speed * horizon_hours, 1)

            # Cap maximum projection distance to avoid unrealistic global wrapping
            distance_km = min(400.0, max(2.0, distance_km))

            # 2. Compute time-aware curved centerline
            centerline_pts: List[List[float]] = [[lat, lon]]
            cur_lat, cur_lon = lat, lon

            # Step hour by hour to trace directional shifts
            steps = min(horizon_hours, len(hourly_forecasts))
            step_hours = max(1, horizon_hours // max(1, steps))

            for step_idx in range(steps):
                forecast_item = hourly_forecasts[step_idx] if step_idx < len(hourly_forecasts) else None
                step_bearing = forecast_item.downwind_bearing_deg if forecast_item else current_bearing
                step_speed = (forecast_item.wind_speed_kmh if forecast_item else current_speed) * settings.PLUME_SPEED_DAMPENING_FACTOR
                step_dist = step_speed * step_hours

                cur_lat, cur_lon = destination_point(cur_lat, cur_lon, step_bearing, step_dist)
                centerline_pts.append([round(cur_lat, 5), round(cur_lon, 5)])

            # End tip of the plume centerline
            tip_lat, tip_lon = centerline_pts[-1]

            # Overall bearing from origin to tip
            overall_bearing = math.degrees(
                math.atan2(
                    math.sin(math.radians(tip_lon - lon)) * math.cos(math.radians(tip_lat)),
                    math.cos(math.radians(lat)) * math.sin(math.radians(tip_lat)) -
                    math.sin(math.radians(lat)) * math.cos(math.radians(tip_lat)) * math.cos(math.radians(tip_lon - lon))
                )
            ) % 360.0

            # 3. Calculate spreading cone width with uncertainty growth
            spread_angle = settings.PLUME_BASE_SPREAD_ANGLE + (horizon_hours * settings.PLUME_UNCERTAINTY_GROWTH_PER_HOUR)
            half_spread = spread_angle / 2.0

            # Left and right boundary angles
            left_bearing = (overall_bearing - half_spread) % 360.0
            right_bearing = (overall_bearing + half_spread) % 360.0

            # Generate polygon perimeter points
            # Origin -> Left arc points -> Tip -> Right arc points -> Back to origin
            left_lat, left_lon = destination_point(lat, lon, left_bearing, distance_km)
            right_lat, right_lon = destination_point(lat, lon, right_bearing, distance_km)

            # Construct smooth perimeter arc
            arc_points: List[List[float]] = []
            num_arc_steps = 7
            for i in range(num_arc_steps + 1):
                interp_bearing = left_bearing + (i / num_arc_steps) * spread_angle
                arc_lat, arc_lon = destination_point(lat, lon, interp_bearing, distance_km)
                arc_points.append([round(arc_lat, 5), round(arc_lon, 5)])

            # Full polygon: origin -> arc points -> origin
            polygon_coords: List[List[float]] = [[lat, lon]] + arc_points + [[lat, lon]]

            confidence = "High" if horizon_hours <= 1 else "Moderate" if horizon_hours <= 3 else "Indicative Screening"

            horizons_features.append(PlumeHorizonFeature(
                horizon_hours=horizon_hours,
                projected_distance_km=distance_km,
                bearing_deg=round(overall_bearing, 1),
                cone_spread_angle_deg=round(spread_angle, 1),
                confidence_rating=confidence,
                polygon_coordinates=polygon_coords,
                centerline_coordinates=centerline_pts
            ))

        return PlumeConeResponse(
            hotspot_id=hotspot_id,
            hotspot_name=hotspot_name,
            centroid_lat=lat,
            centroid_lon=lon,
            current_wind=wind,
            horizons=horizons_features,
            screening_disclaimer=(
                "INDICATIVE SCREENING ONLY: This wind-projected zone represents atmospheric transport "
                "potential based on weather-model wind vectors. It is not a certified fire spread perimeter "
                "or validated smoke concentration forecast."
            ),
            generated_at=datetime.now(timezone.utc).isoformat()
        )


weather_service = WeatherService()
plume_engine = PlumeEngine()
