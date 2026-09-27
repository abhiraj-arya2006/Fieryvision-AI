import os
import time
import asyncio
import logging
import csv
import io
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import httpx

from app.core.config import settings

logger = logging.getLogger("firms_service")

# Cache storage paths for real NASA observations
CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")
)
CACHE_FILE = os.path.join(CACHE_DIR, "firms_cache.json")

# In-memory FIRMS cache state (strictly real NASA observations)
_FIRMS_CACHE: Dict[str, Any] = {
    "data": [],
    "last_fetched": 0.0,
    "last_successful_fetch": None,
    "data_mode": "unavailable",
    "freshness": "unavailable",
    "live_event_count": 0,
    "cached_event_count": 0,
    "api_reachable": False,
    "api_success": False,
    "message": None,
    "simulated_outage": False
}

_FETCH_LOCK = asyncio.Lock()


def _load_persisted_cache():
    """Load previously cached real NASA FIRMS observations from disk if available."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            events = saved.get("events", [])
            last_fetch = saved.get("last_successful_fetch")
            if events:
                _FIRMS_CACHE["data"] = events
                _FIRMS_CACHE["last_successful_fetch"] = last_fetch
                _FIRMS_CACHE["cached_event_count"] = len(events)
                _FIRMS_CACHE["data_mode"] = "cached"
                _FIRMS_CACHE["freshness"] = "cached"
                logger.info(
                    "Loaded %d real NASA FIRMS cached events from disk (fetched at %s)",
                    len(events), last_fetch
                )
        except Exception as exc:
            logger.warning("Failed to load persisted FIRMS cache from %s: %s", CACHE_FILE, exc)


# Initialize persistent cache at module import
_load_persisted_cache()


def _save_persisted_cache(events: List[Dict[str, Any]], fetch_time_iso: str):
    """Save real NASA FIRMS observations to disk cache."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        temp_file = f"{CACHE_FILE}.tmp"
        payload = {
            "last_successful_fetch": fetch_time_iso,
            "event_count": len(events),
            "events": events
        }
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(temp_file, CACHE_FILE)
    except Exception as exc:
        logger.warning("Could not persist FIRMS cache to %s: %s", CACHE_FILE, exc)


def _persist_events_to_db(events: List[Dict[str, Any]]):
    """Persist real observations to the SQLite database for genuine historical analysis."""
    try:
        from app.core.db import SessionLocal
        from app.models.database import ThermalEvent
        db = SessionLocal()
        try:
            sample_ids = [e["event_id"] for e in events[:2000]]
            existing_ids = set(
                row[0] for row in db.query(ThermalEvent.id).filter(ThermalEvent.id.in_(sample_ids)).all()
            )
            to_add = []
            for ev in events[:2000]:
                if ev["event_id"] not in existing_ids:
                    to_add.append(ThermalEvent(
                        id=ev["event_id"],
                        latitude=ev["latitude"],
                        longitude=ev["longitude"],
                        acq_date=ev.get("acq_date", ""),
                        acq_time=ev.get("acq_time", ""),
                        frp=ev.get("frp"),
                        brightness=ev.get("brightness"),
                        confidence=ev.get("confidence"),
                        satellite=ev.get("satellite"),
                        daynight=ev.get("daynight")
                    ))
            if to_add:
                db.bulk_save_objects(to_add)
                db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.debug("Database event persistence note: %s", exc)


def set_simulated_outage(enabled: bool):
    """Enable or disable simulated NASA FIRMS outage for verification testing."""
    _FIRMS_CACHE["simulated_outage"] = enabled
    logger.info("FIRMS simulated outage set to: %s", enabled)

SATELLITE_CODE_MAP = {
    "N20": "NOAA-20",
    "N21": "NOAA-21",
    "N": "Suomi-NPP",
    "1": "Terra",
    "2": "Aqua"
}

CONFIDENCE_MAP = {
    "h": "high",
    "n": "nominal",
    "l": "low"
}

ACTIVE_SENSORS = [
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "VIIRS_SNPP_NRT"
]


async def fetch_firms_active_events(force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], str, Optional[str], int, int, str]:
    """
    Fetch active FIRMS thermal anomalies with WORLD/global coverage.
    Queries multi-sensor VIIRS NRT (NOAA-20, NOAA-21, Suomi-NPP) from NASA EOSDIS.

    Returns:
        (events, data_mode, last_successful_fetch, live_count, cached_count, freshness)

    Data modes / Freshness:
      - 'live': Real NASA request succeeded and live data is served.
      - 'cached': NASA request failed or unreachable; previously fetched REAL NASA data is served.
      - 'unavailable': NASA request failed and NO cached data exists; zero observations returned.
      NEVER returns fabricated or fallback data.
    """
    now_time = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()
    today_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Return fresh in-memory data if cache TTL has not expired
    if (
        not force_refresh
        and _FIRMS_CACHE["data"]
        and (now_time - _FIRMS_CACHE["last_fetched"]) < settings.FIRMS_CACHE_TTL_SECONDS
        and not _FIRMS_CACHE["simulated_outage"]
    ):
        return (
            _FIRMS_CACHE["data"],
            _FIRMS_CACHE["data_mode"],
            _FIRMS_CACHE["last_successful_fetch"],
            _FIRMS_CACHE["live_event_count"],
            _FIRMS_CACHE["cached_event_count"],
            _FIRMS_CACHE["freshness"]
        )

    # 2. Acquire concurrency lock to prevent duplicate concurrent queries to NASA
    async with _FETCH_LOCK:
        # Re-check after acquiring lock
        if (
            not force_refresh
            and _FIRMS_CACHE["data"]
            and (now_time - _FIRMS_CACHE["last_fetched"]) < settings.FIRMS_CACHE_TTL_SECONDS
            and not _FIRMS_CACHE["simulated_outage"]
        ):
            return (
                _FIRMS_CACHE["data"],
                _FIRMS_CACHE["data_mode"],
                _FIRMS_CACHE["last_successful_fetch"],
                _FIRMS_CACHE["live_event_count"],
                _FIRMS_CACHE["cached_event_count"],
                _FIRMS_CACHE["freshness"]
            )

        # Handle simulated outage test mode
        if _FIRMS_CACHE["simulated_outage"]:
            logger.info("FIRMS simulated outage active. Serving cached real NASA data if available.")
            if _FIRMS_CACHE["data"]:
                _FIRMS_CACHE["data_mode"] = "cached"
                _FIRMS_CACHE["freshness"] = "cached"
                _FIRMS_CACHE["live_event_count"] = 0
                _FIRMS_CACHE["cached_event_count"] = len(_FIRMS_CACHE["data"])
                _FIRMS_CACHE["api_reachable"] = False
                _FIRMS_CACHE["api_success"] = False
                _FIRMS_CACHE["message"] = "Simulated NASA FIRMS outage active. Serving cached real observations."
                return (
                    _FIRMS_CACHE["data"],
                    "cached",
                    _FIRMS_CACHE["last_successful_fetch"],
                    0,
                    len(_FIRMS_CACHE["data"]),
                    "cached"
                )
            else:
                _FIRMS_CACHE["data_mode"] = "unavailable"
                _FIRMS_CACHE["freshness"] = "unavailable"
                _FIRMS_CACHE["live_event_count"] = 0
                _FIRMS_CACHE["cached_event_count"] = 0
                _FIRMS_CACHE["api_reachable"] = False
                _FIRMS_CACHE["api_success"] = False
                _FIRMS_CACHE["message"] = "Live NASA FIRMS data unavailable (simulated outage)."
                return ([], "unavailable", None, 0, 0, "unavailable")

        map_key = settings.FIRMS_MAP_KEY
        if not map_key or map_key.strip() == "":
            logger.warning("FIRMS_MAP_KEY not configured. Checking for cached real data.")
            if _FIRMS_CACHE["data"]:
                _FIRMS_CACHE["data_mode"] = "cached"
                _FIRMS_CACHE["freshness"] = "cached"
                _FIRMS_CACHE["live_event_count"] = 0
                _FIRMS_CACHE["cached_event_count"] = len(_FIRMS_CACHE["data"])
                _FIRMS_CACHE["api_reachable"] = False
                _FIRMS_CACHE["api_success"] = False
                _FIRMS_CACHE["message"] = "FIRMS_MAP_KEY not set. Serving cached observations."
                return (
                    _FIRMS_CACHE["data"],
                    "cached",
                    _FIRMS_CACHE["last_successful_fetch"],
                    0,
                    len(_FIRMS_CACHE["data"]),
                    "cached"
                )
            else:
                _FIRMS_CACHE["data_mode"] = "unavailable"
                _FIRMS_CACHE["freshness"] = "unavailable"
                _FIRMS_CACHE["live_event_count"] = 0
                _FIRMS_CACHE["cached_event_count"] = 0
                _FIRMS_CACHE["api_reachable"] = False
                _FIRMS_CACHE["api_success"] = False
                _FIRMS_CACHE["message"] = "Live NASA FIRMS data unavailable (key not configured)."
                return ([], "unavailable", None, 0, 0, "unavailable")

        # 3. Query real NASA FIRMS global feed
        live_events: List[Dict[str, Any]] = []
        api_connected = False
        seen_coords = set()
        any_reachable = False
        last_error_msg: Optional[str] = None
        idx = 1

        async def _fetch_sensor(client: httpx.AsyncClient, sensor_name: str):
            sensor_url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{sensor_name}/world/1"
            try:
                r = await client.get(sensor_url, timeout=30.0)
                if r.status_code == 200:
                    text = r.text.strip()
                    if not text.startswith("Invalid") and "error" not in text.lower()[:80]:
                        return sensor_name, text, True, True, None
                    return sensor_name, None, True, False, f"NASA response notice: {text[:100]}"
                else:
                    return sensor_name, None, True, False, f"HTTP {r.status_code}: {r.text[:100]}"
            except Exception as e:
                logger.warning("Error querying FIRMS sensor %s: %s", sensor_name, e)
                return sensor_name, None, False, False, str(e)

        try:
            async with httpx.AsyncClient() as client:
                fetch_tasks = [_fetch_sensor(client, s) for s in ACTIVE_SENSORS]
                results = await asyncio.gather(*fetch_tasks)

                for sensor_name, csv_text, reachable, success, err_msg in results:
                    if reachable:
                        any_reachable = True
                    if not success or not csv_text:
                        if err_msg:
                            last_error_msg = err_msg
                        continue

                    api_connected = True
                    reader = csv.DictReader(io.StringIO(csv_text))
                    for row in reader:
                        try:
                            lat = float(row.get("latitude", 0.0))
                            lon = float(row.get("longitude", 0.0))

                            coord_key = (round(lat, 3), round(lon, 3), row.get("acq_date"), row.get("acq_time"))
                            if coord_key in seen_coords:
                                continue
                            seen_coords.add(coord_key)

                            sat_code = row.get("satellite", "")
                            sat_name = SATELLITE_CODE_MAP.get(sat_code, sensor_name.replace("_NRT", ""))

                            raw_conf = (row.get("confidence") or "n").lower()
                            conf_name = CONFIDENCE_MAP.get(raw_conf, raw_conf)

                            frp_val = float(row.get("frp", 0.0)) if row.get("frp") else None
                            bright_val = float(row.get("bright_ti4", 0.0)) if row.get("bright_ti4") else None

                            live_events.append({
                                "event_id": f"FIRMS-LIVE-{idx:05d}",
                                "latitude": lat,
                                "longitude": lon,
                                "acq_date": row.get("acq_date", today_date_str),
                                "acq_time": row.get("acq_time", "0000"),
                                "frp": frp_val,
                                "brightness": bright_val,
                                "confidence": conf_name,
                                "satellite": sat_name,
                                "daynight": row.get("daynight", "D"),
                                "source": "NASA_FIRMS"
                            })
                            idx += 1
                        except (ValueError, KeyError) as pe:
                            logger.debug("Row parse error: %s", pe)
                            continue

            if api_connected and live_events:
                # Successful fetch: update in-memory cache and persist to disk
                _FIRMS_CACHE["data"] = live_events
                _FIRMS_CACHE["last_fetched"] = now_time
                _FIRMS_CACHE["last_successful_fetch"] = now_iso
                _FIRMS_CACHE["data_mode"] = "live"
                _FIRMS_CACHE["freshness"] = "live"
                _FIRMS_CACHE["live_event_count"] = len(live_events)
                _FIRMS_CACHE["cached_event_count"] = 0
                _FIRMS_CACHE["api_reachable"] = True
                _FIRMS_CACHE["api_success"] = True
                _FIRMS_CACHE["message"] = None

                _save_persisted_cache(live_events, now_iso)
                _persist_events_to_db(live_events)

                logger.info(
                    "NASA FIRMS API global query active: fetched %d live WORLD observations.",
                    len(live_events)
                )
                return (
                    live_events,
                    "live",
                    now_iso,
                    len(live_events),
                    0,
                    "live"
                )

        except Exception as e:
            logger.warning("FIRMS API connection attempt failed: %s", e)
            last_error_msg = str(e)

        # 4. Outage fallback to previously cached real NASA observations
        if _FIRMS_CACHE["data"]:
            _FIRMS_CACHE["last_fetched"] = now_time
            _FIRMS_CACHE["data_mode"] = "cached"
            _FIRMS_CACHE["freshness"] = "cached"
            _FIRMS_CACHE["live_event_count"] = 0
            _FIRMS_CACHE["cached_event_count"] = len(_FIRMS_CACHE["data"])
            _FIRMS_CACHE["api_reachable"] = any_reachable
            _FIRMS_CACHE["api_success"] = False
            _FIRMS_CACHE["message"] = last_error_msg or "NASA FIRMS query failed. Serving cached observations."

            logger.info(
                "Serving %d cached real NASA observations (last fetched %s)",
                len(_FIRMS_CACHE["data"]), _FIRMS_CACHE["last_successful_fetch"]
            )
            return (
                _FIRMS_CACHE["data"],
                "cached",
                _FIRMS_CACHE["last_successful_fetch"],
                0,
                len(_FIRMS_CACHE["data"]),
                "cached"
            )

        # 5. Outage and no cache exists: return 0 events with unavailable status
        _FIRMS_CACHE["last_fetched"] = now_time
        _FIRMS_CACHE["data_mode"] = "unavailable"
        _FIRMS_CACHE["freshness"] = "unavailable"
        _FIRMS_CACHE["live_event_count"] = 0
        _FIRMS_CACHE["cached_event_count"] = 0
        _FIRMS_CACHE["api_reachable"] = any_reachable
        _FIRMS_CACHE["api_success"] = False
        _FIRMS_CACHE["message"] = last_error_msg or "Live NASA FIRMS data unavailable."

        logger.warning("NASA FIRMS unavailable and no cache exists. Returning 0 observations.")
        return ([], "unavailable", None, 0, 0, "unavailable")


async def get_firms_status(force_check: bool = False) -> Dict[str, Any]:
    """
    Check NASA FIRMS connection and cache status.
    Does not expose the API key.
    """
    now_time = time.time()
    if force_check or not _FIRMS_CACHE["data"] or (now_time - _FIRMS_CACHE["last_fetched"]) >= settings.FIRMS_CACHE_TTL_SECONDS:
        await fetch_firms_active_events(force_refresh=force_check)

    return {
        "api_reachable": bool(_FIRMS_CACHE.get("api_reachable", False)),
        "api_success": bool(_FIRMS_CACHE.get("api_success", False)),
        "live_event_count": int(_FIRMS_CACHE.get("live_event_count", 0)),
        "cached_event_count": int(_FIRMS_CACHE.get("cached_event_count", 0)),
        "data_mode": str(_FIRMS_CACHE.get("data_mode", "unavailable")),
        "freshness": str(_FIRMS_CACHE.get("freshness", "unavailable")),
        "source": "NASA_FIRMS",
        "coverage": "WORLD",
        "last_successful_fetch": _FIRMS_CACHE.get("last_successful_fetch"),
        "message": _FIRMS_CACHE.get("message"),
        "simulated_outage": bool(_FIRMS_CACHE.get("simulated_outage", False))
    }

