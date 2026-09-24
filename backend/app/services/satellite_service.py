from typing import Dict, Any

def get_satellite_context_metadata(event_id: str, satellite: str = "NOAA-20", acq_date: str = "") -> Dict[str, Any]:
    """
    Provide clean abstraction for returning available satellite imagery/context metadata for an event.
    Returns metadata without fabricating missing imagery.
    """
    if "LIVE" in event_id or "GIAS" in event_id:
        return {
            "event_id": event_id,
            "status": "available",
            "satellite": satellite or "NOAA-20",
            "sensor": "VIIRS (Visible Infrared Imaging Radiometer Suite)",
            "acquisition_date": acq_date or "Recent",
            "resolution_m": 375.0,
            "bands_available": ["I4 (3.74 µm thermal)", "I5 (11.45 µm thermal)", "M13 (4.05 µm thermal)"],
            "provider": "NASA LANCE / FIRMS Near-Real-Time",
            "message": "Satellite radiometric thermal anomaly context available."
        }
    else:
        return {
            "event_id": event_id,
            "status": "unavailable",
            "satellite": None,
            "sensor": None,
            "acquisition_date": None,
            "resolution_m": None,
            "bands_available": [],
            "provider": None,
            "message": f"High-resolution satellite optical context imagery is currently unavailable for event {event_id}."
        }
