from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Integer
from app.core.db import Base

class ThermalEvent(Base):
    __tablename__ = "thermal_events"

    id = Column(String, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    acq_date = Column(String, nullable=False)
    acq_time = Column(String, nullable=False)
    frp = Column(Float, nullable=True)
    brightness = Column(Float, nullable=True)
    confidence = Column(String, nullable=True)
    satellite = Column(String, nullable=True)
    daynight = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class IndustrialSite(Base):
    __tablename__ = "industrial_sites"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    site_type = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    operating_status = Column(String, default="active")

class EventAnalysis(Base):
    __tablename__ = "event_analysis"

    event_id = Column(String, primary_key=True, index=True)
    classification = Column(String, nullable=False)
    classification_method = Column(String, nullable=False)  # evidence_based, supervised_ml, cached, active, unclassified
    classification_confidence = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=False)
    priority = Column(String, nullable=False)
    landcover = Column(String, nullable=True)
    evidence_json = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)  # ACTIVE, CONTAINED, EXTINGUISHED, MONITORING
    classification = Column(String, nullable=False, index=True)  # ACTIVE HOTSPOT, PERSISTENT HOTSPOT, EMERGING HOTSPOT, etc.
    centroid_lat = Column(Float, nullable=False, index=True)
    centroid_lon = Column(Float, nullable=False, index=True)
    min_lat = Column(Float, nullable=False)
    min_lon = Column(Float, nullable=False)
    max_lat = Column(Float, nullable=False)
    max_lon = Column(Float, nullable=False)
    area_sq_km = Column(Float, default=1.0)
    event_count = Column(Integer, default=1)
    unique_acquisitions = Column(Integer, default=1)
    duration_hours = Column(Float, default=0.0)
    first_seen = Column(String, nullable=False)
    last_seen = Column(String, nullable=False)
    average_frp = Column(Float, default=0.0)
    max_frp = Column(Float, default=0.0)
    frp_trend = Column(String, default="STABLE")  # INCREASING, DECREASING, STABLE, SURGING
    average_brightness = Column(Float, default=320.0)
    max_brightness = Column(Float, default=330.0)
    persistence_score = Column(Float, default=0.5)
    recurrence_score = Column(Float, default=0.3)
    growth_rate = Column(Float, default=0.0)  # percentage e.g. +45.2%
    growth_status = Column(String, default="STABLE")  # EXPANDING, CONTRACTING, STABLE, MOVING, NEWLY_FORMED
    spatial_density = Column(Float, default=0.0)  # events / km2
    hotspot_score = Column(Float, default=0.5)  # 0.0 - 1.0 composite score
    risk_score = Column(Float, default=50.0)  # 0.0 - 100.0 triage score
    risk_tier = Column(String, default="MODERATE", index=True)  # CRITICAL, HIGH, MODERATE, LOW
    confidence = Column(Float, default=0.8)
    anomaly_score = Column(Float, default=0.1)
    country = Column(String, index=True)
    continent = Column(String, index=True)
    region = Column(String, nullable=True)
    nearest_city = Column(String, nullable=True)
    dominant_landcover = Column(String, default="Unknown")
    landcover_classes_json = Column(Text, default="[]")
    nearby_facilities_count = Column(Integer, default=0)
    nearest_facility_name = Column(String, nullable=True)
    nearest_facility_distance_m = Column(Float, nullable=True)
    reason_codes_json = Column(Text, default="[]")
    uncertainty_note = Column(String, nullable=True)
    source_satellites_json = Column(Text, default="[]")
    daynight_distribution_json = Column(Text, default="{}")
    detections_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    model_version = Column(String, default="v10.5-global-engine")


class HotspotSnapshot(Base):
    __tablename__ = "hotspot_snapshots"

    id = Column(String, primary_key=True, index=True)
    hotspot_id = Column(String, index=True, nullable=False)
    timestamp = Column(String, nullable=False)
    event_count = Column(Integer, default=1)
    area_sq_km = Column(Float, default=1.0)
    average_frp = Column(Float, default=0.0)
    max_frp = Column(Float, default=0.0)
    risk_score = Column(Float, default=50.0)
    growth_rate = Column(Float, default=0.0)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
