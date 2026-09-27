import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from app.core.geo import haversine_distance_m

def build_spatial_index(events: List[Dict[str, Any]]) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
    """Pre-index events into 0.1-degree spatial bins (~11km) for fast local lookups."""
    index: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for ev in events:
        lat = ev.get("latitude")
        lon = ev.get("longitude")
        if lat is not None and lon is not None:
            key = (int(lat * 10), int(lon * 10))
            index.setdefault(key, []).append(ev)
    return index

def analyze_temporal_persistence(
    target_lat: float,
    target_lon: float,
    all_events: List[Dict[str, Any]],
    spatial_radius_m: float = 500.0,
    spatial_index: Optional[Dict[Tuple[int, int], List[Dict[str, Any]]]] = None
) -> Dict[str, Any]:
    """
    Analyze temporal persistence and FRP statistics for events near (target_lat, target_lon).
    """
    nearby_events = []
    lat_delta = (spatial_radius_m / 111000.0) * 1.5
    lon_delta = (spatial_radius_m / (111000.0 * max(0.1, abs(math.cos(math.radians(target_lat)))))) * 1.5

    if spatial_index is not None:
        target_bin_lat = int(target_lat * 10)
        target_bin_lon = int(target_lon * 10)
        candidate_events = []
        for dlat in (-1, 0, 1):
            for dlon in (-1, 0, 1):
                cell = spatial_index.get((target_bin_lat + dlat, target_bin_lon + dlon))
                if cell:
                    candidate_events.extend(cell)
    else:
        candidate_events = all_events

    for event in candidate_events:
        elat = event.get("latitude")
        elon = event.get("longitude")
        if elat is None or elon is None:
            continue
        if abs(elat - target_lat) > lat_delta or abs(elon - target_lon) > lon_delta:
            continue
        dist = haversine_distance_m(target_lat, target_lon, elat, elon)
        if dist <= spatial_radius_m:
            nearby_events.append(event)

    if not nearby_events:
        return {
            "detections_7d": 0,
            "detections_30d": 0,
            "unique_detection_days": 0,
            "average_frp": None,
            "maximum_frp": None,
            "first_seen": None,
            "last_seen": None,
            "persistence": "single_observation"
        }

    # Date parsing
    dates = []
    frp_values = []

    for ev in nearby_events:
        acq_date_str = ev.get("acq_date")
        if acq_date_str:
            try:
                dt = datetime.strptime(acq_date_str, "%Y-%m-%d")
                dates.append(dt)
            except ValueError:
                pass
        
        frp = ev.get("frp")
        if frp is not None and isinstance(frp, (int, float)):
            frp_values.append(float(frp))

    dates.sort()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    det_7d = sum(1 for d in dates if d >= seven_days_ago) if dates else len(nearby_events)
    det_30d = sum(1 for d in dates if d >= thirty_days_ago) if dates else len(nearby_events)

    unique_days = len(set(d.date() for d in dates)) if dates else 1

    avg_frp = round(sum(frp_values) / len(frp_values), 2) if frp_values else None
    max_frp = round(max(frp_values), 2) if frp_values else None

    first_seen_str = dates[0].strftime("%Y-%m-%d") if dates else nearby_events[0].get("acq_date")
    last_seen_str = dates[-1].strftime("%Y-%m-%d") if dates else nearby_events[-1].get("acq_date")

    # Determine persistence rating
    if unique_days >= 5 or det_30d >= 10:
        persistence = "high_persistence"
    elif unique_days >= 3 or det_7d >= 3:
        persistence = "recurrent_heat_source"
    elif len(nearby_events) > 1:
        persistence = "moderate_persistence"
    else:
        persistence = "single_observation"

    return {
        "detections_7d": det_7d,
        "detections_30d": det_30d,
        "unique_detection_days": unique_days,
        "average_frp": avg_frp,
        "maximum_frp": max_frp,
        "first_seen": first_seen_str,
        "last_seen": last_seen_str,
        "persistence": persistence
    }
