from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.core.geo import haversine_distance_m

def analyze_temporal_persistence(
    target_lat: float,
    target_lon: float,
    all_events: List[Dict[str, Any]],
    spatial_radius_m: float = 500.0
) -> Dict[str, Any]:
    """
    Analyze temporal persistence and FRP statistics for events near (target_lat, target_lon).
    """
    nearby_events = []

    for event in all_events:
        dist = haversine_distance_m(target_lat, target_lon, event["latitude"], event["longitude"])
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
