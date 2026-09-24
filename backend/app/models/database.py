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
