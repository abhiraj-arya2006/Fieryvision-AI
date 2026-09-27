import pytest
from app.core.db import SessionLocal
from app.models.database import Hotspot, HotspotSnapshot
from app.services.hotspot_service import hotspot_engine

SAMPLE_FIRMS_EVENTS = [
    # USA cluster (California)
    {"event_id": "TEST-USA-1", "latitude": 39.51, "longitude": -121.54, "frp": 65.0, "brightness": 345.0, "confidence": "high", "satellite": "NOAA-20", "acq_date": "2026-09-20", "acq_time": "1200", "daynight": "D"},
    {"event_id": "TEST-USA-2", "latitude": 39.52, "longitude": -121.55, "frp": 72.0, "brightness": 350.0, "confidence": "high", "satellite": "NOAA-21", "acq_date": "2026-09-20", "acq_time": "1300", "daynight": "D"},
    {"event_id": "TEST-USA-3", "latitude": 39.53, "longitude": -121.53, "frp": 55.0, "brightness": 338.0, "confidence": "nominal", "satellite": "NOAA-20", "acq_date": "2026-09-21", "acq_time": "1230", "daynight": "D"},

    # India cluster (Punjab)
    {"event_id": "TEST-IND-1", "latitude": 30.875, "longitude": 75.898, "frp": 45.0, "brightness": 335.0, "confidence": "high", "satellite": "NOAA-20", "acq_date": "2026-09-20", "acq_time": "1800", "daynight": "N"},
    {"event_id": "TEST-IND-2", "latitude": 30.876, "longitude": 75.899, "frp": 50.0, "brightness": 340.0, "confidence": "high", "satellite": "NOAA-21", "acq_date": "2026-09-21", "acq_time": "1830", "daynight": "N"},
    {"event_id": "TEST-IND-3", "latitude": 30.877, "longitude": 75.897, "frp": 40.0, "brightness": 330.0, "confidence": "nominal", "satellite": "NOAA-20", "acq_date": "2026-09-22", "acq_time": "1900", "daynight": "N"},

    # Europe cluster (Greece)
    {"event_id": "TEST-EU-1", "latitude": 40.51, "longitude": 22.51, "frp": 35.0, "brightness": 325.0, "confidence": "nominal", "satellite": "NOAA-20", "acq_date": "2026-09-20", "acq_time": "1100", "daynight": "D"},
    {"event_id": "TEST-EU-2", "latitude": 40.52, "longitude": 22.52, "frp": 38.0, "brightness": 328.0, "confidence": "nominal", "satellite": "NOAA-21", "acq_date": "2026-09-21", "acq_time": "1130", "daynight": "D"},
    {"event_id": "TEST-EU-3", "latitude": 40.53, "longitude": 22.50, "frp": 30.0, "brightness": 320.0, "confidence": "low", "satellite": "NOAA-20", "acq_date": "2026-09-22", "acq_time": "1200", "daynight": "D"},
]

@pytest.fixture(autouse=True, scope="session")
def setup_test_clusters():
    """Cluster test FIRMS observations dynamically so hotspot and incident endpoints can be tested."""
    # Clean up any leftover test data first
    db = SessionLocal()
    try:
        db.query(HotspotSnapshot).filter(HotspotSnapshot.hotspot_id.like("HS-REAL-%")).delete(synchronize_session=False)
        db.query(Hotspot).filter(Hotspot.id.like("HS-REAL-%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    
    hotspot_engine.sync_hotspots_from_firms(SAMPLE_FIRMS_EVENTS)
    yield
    db = SessionLocal()
    try:
        db.query(HotspotSnapshot).filter(HotspotSnapshot.hotspot_id.like("HS-REAL-%")).delete(synchronize_session=False)
        db.query(Hotspot).filter(Hotspot.id.like("HS-REAL-%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
