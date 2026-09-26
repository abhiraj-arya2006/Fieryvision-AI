from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from app.core.config import settings
from app.core.geo import validate_coordinates, haversine_distance_m, is_within_giaspura_area
from app.schemas.event import (
    CanonicalEventSchema,
    ActiveEventsResponse,
    HealthResponse,
    LocationAnalysisRequest,
    LocationAnalysisResponse,
    FacilitiesResponse,
    FacilitySchema,
    StatisticsResponse,
    SatelliteContextResponse,
    ChatRequest,
    ChatResponse
)
from app.services.firms_service import fetch_firms_active_events, HISTORICAL_GIASPURA_EVENTS
from app.services.industrial_service import (
    get_all_facilities,
    find_nearest_facility,
    is_inside_industrial_zone,
    get_landcover_context
)
from app.services.temporal_service import analyze_temporal_persistence
from app.services.evidence_service import evaluate_evidence
from app.services.anomaly_service import detect_thermal_anomaly
from app.services.satellite_service import get_satellite_context_metadata
from app.services.llm_service import generate_explanation, generate_chat_response


router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health():
    """
    Health check endpoint returning system status, FIRMS availability, and classification mode.
    """
    firms_key_present = bool(settings.FIRMS_MAP_KEY and settings.FIRMS_MAP_KEY.strip())
    return HealthResponse(
        status="ok",
        service="FieryVision API",
        firms_available=firms_key_present,
        classification_mode="evidence_based",  # Strict requirement: supervised ML unavailable without true ground-truth labels
        data_mode="active" if firms_key_present else "cached"
    )

@router.get("/active-events", response_model=ActiveEventsResponse, tags=["Events"])
async def get_active_events():
    """
    Retrieve active/recent FIRMS thermal anomalies filtered to Giaspura study area.
    """
    raw_events, data_mode, last_updated = await fetch_firms_active_events()
    
    canonical_events: List[CanonicalEventSchema] = []
    
    for ev in raw_events:
        lat = ev["latitude"]
        lon = ev["longitude"]
        
        fac, dist_m = find_nearest_facility(lat, lon)
        inside_ind = is_inside_industrial_zone(lat, lon)
        landcover = get_landcover_context(lat, lon)
        temporal = analyze_temporal_persistence(lat, lon, raw_events)
        
        # ML Anomaly Detection (Isolation Forest)
        is_anom, anom_score = detect_thermal_anomaly(ev, temporal)
        
        evidence_eval = evaluate_evidence(
            lat=lat,
            lon=lon,
            nearest_facility=fac,
            distance_to_facility_m=dist_m,
            inside_industrial_zone=inside_ind,
            landcover=landcover,
            temporal_summary=temporal,
            frp=ev.get("frp"),
            daynight=ev.get("daynight"),
            anomaly_score=anom_score,
            anomaly_flag=is_anom
        )
        
        canonical_ev = CanonicalEventSchema(
            event_id=ev["event_id"],
            latitude=lat,
            longitude=lon,
            acq_date=ev.get("acq_date", ""),
            acq_time=ev.get("acq_time", ""),
            frp=ev.get("frp"),
            brightness=ev.get("brightness"),
            confidence=ev.get("confidence"),
            satellite=ev.get("satellite"),
            daynight=ev.get("daynight"),
            nearest_facility_name=fac["name"] if fac else None,
            nearest_facility_type=fac["site_type"] if fac else None,
            distance_to_facility_m=round(dist_m, 1) if fac else None,
            inside_industrial_zone=inside_ind,
            landcover=landcover,
            detections_7d=temporal["detections_7d"],
            detections_30d=temporal["detections_30d"],
            unique_detection_days=temporal["unique_detection_days"],
            average_frp=temporal["average_frp"],
            maximum_frp=temporal["maximum_frp"],
            first_seen=temporal["first_seen"],
            last_seen=temporal["last_seen"],
            persistence=temporal["persistence"],
            classification=evidence_eval["classification"],
            classification_method=evidence_eval["classification_method"],
            classification_confidence=evidence_eval["classification_confidence"],
            risk_score=evidence_eval["risk_score"],
            priority=evidence_eval["priority"],
            anomaly_score=anom_score,
            is_anomaly=is_anom,
            anomaly_flag=is_anom,
            evidence=evidence_eval["evidence"],
            explanation=None
        )
        canonical_events.append(canonical_ev)

    return ActiveEventsResponse(
        total=len(canonical_events),
        data_mode=data_mode,
        last_updated=last_updated,
        giaspura_center={"latitude": settings.GIASPURA_LAT, "longitude": settings.GIASPURA_LON},
        radius_km=settings.GIASPURA_RADIUS_KM,
        events=canonical_events
    )

@router.get("/events/{event_id}", response_model=CanonicalEventSchema, tags=["Events"])
async def get_event_details(event_id: str = Path(..., description="Target event ID")):
    """
    Get complete available analysis for a single thermal event by ID.
    """
    raw_events, data_mode, _ = await fetch_firms_active_events()
    target_ev = next((e for e in raw_events if e["event_id"] == event_id), None)
    
    if not target_ev:
        # Check historical list fallback
        target_ev = next((e for e in HISTORICAL_GIASPURA_EVENTS if e["event_id"] == event_id), None)

    if not target_ev:
        raise HTTPException(status_code=404, detail=f"Thermal event '{event_id}' not found.")

    lat = target_ev["latitude"]
    lon = target_ev["longitude"]
    
    fac, dist_m = find_nearest_facility(lat, lon)
    inside_ind = is_inside_industrial_zone(lat, lon)
    landcover = get_landcover_context(lat, lon)
    temporal = analyze_temporal_persistence(lat, lon, raw_events)
    
    # ML Anomaly Detection (Isolation Forest)
    is_anom, anom_score = detect_thermal_anomaly(target_ev, temporal)

    evidence_eval = evaluate_evidence(
        lat=lat,
        lon=lon,
        nearest_facility=fac,
        distance_to_facility_m=dist_m,
        inside_industrial_zone=inside_ind,
        landcover=landcover,
        temporal_summary=temporal,
        frp=target_ev.get("frp"),
        daynight=target_ev.get("daynight"),
        anomaly_score=anom_score,
        anomaly_flag=is_anom
    )

    analysis_payload = {
        "event_id": event_id,
        "latitude": lat,
        "longitude": lon,
        "classification": evidence_eval["classification"],
        "classification_method": evidence_eval["classification_method"],
        "risk_score": evidence_eval["risk_score"],
        "priority": evidence_eval["priority"],
        "nearest_facility_name": fac["name"] if fac else "None",
        "distance_to_facility_m": round(dist_m, 1) if fac else None,
        "landcover": landcover,
        "evidence": evidence_eval["evidence"],
        "anomaly_score": anom_score,
        "is_anomaly": is_anom
    }

    explanation_text, _ = await generate_explanation(analysis_payload)

    return CanonicalEventSchema(
        event_id=event_id,
        latitude=lat,
        longitude=lon,
        acq_date=target_ev.get("acq_date", ""),
        acq_time=target_ev.get("acq_time", ""),
        frp=target_ev.get("frp"),
        brightness=target_ev.get("brightness"),
        confidence=target_ev.get("confidence"),
        satellite=target_ev.get("satellite"),
        daynight=target_ev.get("daynight"),
        nearest_facility_name=fac["name"] if fac else None,
        nearest_facility_type=fac["site_type"] if fac else None,
        distance_to_facility_m=round(dist_m, 1) if fac else None,
        inside_industrial_zone=inside_ind,
        landcover=landcover,
        detections_7d=temporal["detections_7d"],
        detections_30d=temporal["detections_30d"],
        unique_detection_days=temporal["unique_detection_days"],
        average_frp=temporal["average_frp"],
        maximum_frp=temporal["maximum_frp"],
        first_seen=temporal["first_seen"],
        last_seen=temporal["last_seen"],
        persistence=temporal["persistence"],
        classification=evidence_eval["classification"],
        classification_method=evidence_eval["classification_method"],
        classification_confidence=evidence_eval["classification_confidence"],
        risk_score=evidence_eval["risk_score"],
        priority=evidence_eval["priority"],
        anomaly_score=anom_score,
        is_anomaly=is_anom,
        anomaly_flag=is_anom,
        evidence=evidence_eval["evidence"],
        explanation=explanation_text
    )

@router.get("/facilities", response_model=FacilitiesResponse, tags=["Facilities"])
async def get_facilities():
    """
    Retrieve cached industrial/geospatial facilities for Giaspura study area.
    """
    facilities_list = get_all_facilities()
    facility_schemas = [FacilitySchema(**fac) for fac in facilities_list]
    return FacilitiesResponse(
        total=len(facility_schemas),
        facilities=facility_schemas
    )

@router.get("/statistics", response_model=StatisticsResponse, tags=["Statistics"])
async def get_statistics():
    """
    Return summary statistics distinguishing classified vs unclassified events and risk priorities.
    """
    raw_events, data_mode, _ = await fetch_firms_active_events()
    
    total = len(raw_events)
    industrial_cnt = 0
    persistent_cnt = 0
    natural_cnt = 0
    agricultural_cnt = 0
    critical_priority_cnt = 0
    high_priority_cnt = 0
    moderate_priority_cnt = 0
    low_priority_cnt = 0
    classified_cnt = 0
    unclassified_cnt = 0

    for ev in raw_events:
        lat = ev["latitude"]
        lon = ev["longitude"]
        fac, dist_m = find_nearest_facility(lat, lon)
        inside_ind = is_inside_industrial_zone(lat, lon)
        landcover = get_landcover_context(lat, lon)
        temporal = analyze_temporal_persistence(lat, lon, raw_events)
        
        is_anom, anom_score = detect_thermal_anomaly(ev, temporal)

        evidence_eval = evaluate_evidence(
            lat=lat,
            lon=lon,
            nearest_facility=fac,
            distance_to_facility_m=dist_m,
            inside_industrial_zone=inside_ind,
            landcover=landcover,
            temporal_summary=temporal,
            frp=ev.get("frp"),
            daynight=ev.get("daynight"),
            anomaly_score=anom_score,
            anomaly_flag=is_anom
        )

        cls = evidence_eval["classification"]
        prio = str(evidence_eval["priority"]).lower()
        
        if cls != "unclassified":
            classified_cnt += 1
            if cls == "industrial_heat_source":
                industrial_cnt += 1
            elif cls == "agricultural_burning":
                agricultural_cnt += 1
            elif cls == "natural_fire":
                natural_cnt += 1
        else:
            unclassified_cnt += 1

        if temporal.get("persistence") in ["high_persistence", "recurrent_heat_source", "Persistent"]:
            persistent_cnt += 1

        if prio == "critical":
            critical_priority_cnt += 1
        elif prio == "high":
            high_priority_cnt += 1
        elif prio in ["moderate", "medium"]:
            moderate_priority_cnt += 1
        else:
            low_priority_cnt += 1

    return StatisticsResponse(
        total_events=total,
        industrial_events=industrial_cnt,
        persistent_events=persistent_cnt,
        natural_events=natural_cnt,
        agricultural_events=agricultural_cnt,
        critical_priority_events=critical_priority_cnt,
        high_priority_events=high_priority_cnt,
        moderate_priority_events=moderate_priority_cnt,
        low_priority_events=low_priority_cnt,
        classified_events=classified_cnt,
        unclassified_events=unclassified_cnt,
        classification_mode="evidence_based"
    )

@router.post("/analyse-location", response_model=LocationAnalysisResponse, tags=["Analysis"])
async def analyse_location(payload: LocationAnalysisRequest):
    """
    Coordinate-based AI investigation for arbitrary lat/lon input.
    Validates coordinates, evaluates nearby anomalies, facilities, landcover, temporal history,
    computes evidence-based risk & ML anomaly score, and requests optional Qwen explanation.
    """
    valid, err_msg = validate_coordinates(payload.latitude, payload.longitude)
    if not valid:
        raise HTTPException(status_code=400, detail=err_msg)

    lat = payload.latitude
    lon = payload.longitude

    dist_to_giaspura = haversine_distance_m(lat, lon, settings.GIASPURA_LAT, settings.GIASPURA_LON)
    in_zone = dist_to_giaspura <= (settings.GIASPURA_RADIUS_KM * 1000.0)

    raw_events, data_mode, _ = await fetch_firms_active_events()

    # Find thermal anomalies within 1000m
    nearby_thermal = [
        ev for ev in raw_events
        if haversine_distance_m(lat, lon, ev["latitude"], ev["longitude"]) <= 1000.0
    ]
    thermal_detected = len(nearby_thermal) > 0

    fac, dist_m = find_nearest_facility(lat, lon)
    inside_ind = is_inside_industrial_zone(lat, lon)
    landcover = get_landcover_context(lat, lon)
    temporal = analyze_temporal_persistence(lat, lon, raw_events)

    target_ev_data = nearby_thermal[0] if nearby_thermal else {"latitude": lat, "longitude": lon}
    is_anom, anom_score = detect_thermal_anomaly(target_ev_data, temporal) if thermal_detected else (False, 0.0)

    frp_val = nearby_thermal[0].get("frp") if nearby_thermal else None
    daynight_val = nearby_thermal[0].get("daynight") if nearby_thermal else None

    evidence_eval = evaluate_evidence(
        lat=lat,
        lon=lon,
        nearest_facility=fac,
        distance_to_facility_m=dist_m,
        inside_industrial_zone=inside_ind,
        landcover=landcover,
        temporal_summary=temporal,
        frp=frp_val,
        daynight=daynight_val,
        anomaly_score=anom_score,
        anomaly_flag=is_anom
    )

    assessment_mode = "evidence_based" if thermal_detected else ("no_activity" if in_zone else "insufficient_evidence")

    analysis_payload = {
        "event_id": f"COORD-({lat:.4f},{lon:.4f})",
        "latitude": lat,
        "longitude": lon,
        "classification": evidence_eval["classification"],
        "classification_method": evidence_eval["classification_method"],
        "risk_score": evidence_eval["risk_score"],
        "priority": evidence_eval["priority"],
        "nearest_facility_name": fac["name"] if fac else "None",
        "distance_to_facility_m": round(dist_m, 1) if fac else None,
        "landcover": landcover,
        "evidence": evidence_eval["evidence"],
        "anomaly_score": anom_score,
        "is_anomaly": is_anom
    }

    explanation_text, _ = await generate_explanation(analysis_payload)

    return LocationAnalysisResponse(
        latitude=lat,
        longitude=lon,
        in_giaspura_zone=in_zone,
        distance_to_giaspura_center_m=round(dist_to_giaspura, 1),
        thermal_activity_detected=thermal_detected,
        assessment_mode=assessment_mode,
        active_anomalies_count=len(nearby_thermal),
        nearest_facility_name=fac["name"] if fac else None,
        nearest_facility_type=fac["site_type"] if fac else None,
        distance_to_facility_m=round(dist_m, 1) if fac else None,
        inside_industrial_zone=inside_ind,
        landcover=landcover,
        temporal_summary=temporal,
        classification=evidence_eval["classification"] if thermal_detected else "unclassified",
        classification_method=evidence_eval["classification_method"],
        classification_confidence=evidence_eval["classification_confidence"] if thermal_detected else None,
        risk_score=evidence_eval["risk_score"] if thermal_detected else 0.0,
        priority=evidence_eval["priority"] if thermal_detected else "low",
        anomaly_score=anom_score if thermal_detected else 0.0,
        is_anomaly=is_anom if thermal_detected else False,
        anomaly_flag=is_anom if thermal_detected else False,
        evidence=evidence_eval["evidence"],
        explanation=explanation_text
    )

@router.get("/satellite-context/{event_id}", response_model=SatelliteContextResponse, tags=["Satellite"])
async def get_satellite_context(event_id: str = Path(..., description="Target event ID")):
    """
    Retrieve satellite context imagery metadata for specified event.
    """
    raw_events, _, _ = await fetch_firms_active_events()
    target_ev = next((e for e in raw_events if e["event_id"] == event_id), None)
    
    if target_ev:
        meta = get_satellite_context_metadata(
            event_id,
            satellite=target_ev.get("satellite", "NOAA-20"),
            acq_date=target_ev.get("acq_date", "")
        )
    else:
        meta = get_satellite_context_metadata(event_id)
        
    return SatelliteContextResponse(**meta)


@router.post("/chat", response_model=ChatResponse, tags=["AI"])
async def chat(payload: ChatRequest):
    """
    Answer a user question grounded strictly in the provided FieryVision investigation context.
    Uses local Ollama with qwen2.5:14b. Returns concise bullet-point response.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    context = payload.context or {}
    response_text, llm_ok = await generate_chat_response(payload.question, context)
    return ChatResponse(
        response=response_text or "- AI explanation unavailable — Ollama/Qwen service is offline.",
        llm_available=llm_ok
    )


# =====================================================================
# PHASE 10.5: GLOBAL HOTSPOT INTELLIGENCE SYSTEM ENDPOINTS
# =====================================================================

from app.schemas.hotspot import (
    HotspotsListResponse,
    HotspotSummarySchema,
    HotspotDetailSchema,
    HotspotSnapshotSchema,
    HotspotAnalyticsResponse,
    HotspotAlertSchema
)
from app.services.hotspot_service import hotspot_engine


@router.get("/hotspots", response_model=HotspotsListResponse, tags=["Hotspots"])
async def get_hotspots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    continent: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    risk_tier: Optional[str] = Query(None),
    min_risk: Optional[float] = Query(None),
    min_frp: Optional[float] = Query(None),
    min_persistence: Optional[float] = Query(None),
    sort_by: str = Query("risk_score"),
    order: str = Query("desc")
):
    """
    Retrieve paginated global hotspots with comprehensive filtering, spatial bounds, and sorting.
    """
    return hotspot_engine.list_hotspots(
        page=page,
        page_size=page_size,
        status=status,
        classification=classification,
        continent=continent,
        country=country,
        risk_tier=risk_tier,
        min_risk=min_risk,
        min_frp=min_frp,
        min_persistence=min_persistence,
        sort_by=sort_by,
        order=order
    )


@router.get("/hotspots/analytics", response_model=HotspotAnalyticsResponse, tags=["Hotspots"])
async def get_hotspot_analytics():
    """
    Retrieve global hotspot dashboard analytics, classification counts, and regional breakdown.
    """
    return hotspot_engine.get_global_analytics()


@router.get("/hotspots/alerts", response_model=List[HotspotAlertSchema], tags=["Hotspots"])
async def get_hotspot_alerts():
    """
    Retrieve active objective alert-ready hotspot events (extreme FRP, rapid expansion, critical risk).
    """
    return hotspot_engine.get_hotspot_alerts()


@router.get("/hotspots/active", response_model=List[HotspotSummarySchema], tags=["Hotspots"])
async def get_active_hotspots():
    """
    Shortcut endpoint to retrieve all currently active global hotspots.
    """
    res = hotspot_engine.list_hotspots(status="ACTIVE", page_size=100)
    return res.items


@router.get("/hotspots/emerging", response_model=List[HotspotSummarySchema], tags=["Hotspots"])
async def get_emerging_hotspots():
    """
    Shortcut endpoint to retrieve early-warning emerging hotspots with rapid growth.
    """
    res = hotspot_engine.list_hotspots(classification="EMERGING", page_size=50)
    return res.items


@router.get("/hotspots/persistent", response_model=List[HotspotSummarySchema], tags=["Hotspots"])
async def get_persistent_hotspots():
    """
    Shortcut endpoint to retrieve persistent multi-pass hotspots.
    """
    res = hotspot_engine.list_hotspots(classification="PERSISTENT", page_size=50)
    return res.items


@router.get("/hotspots/high-risk", response_model=List[HotspotSummarySchema], tags=["Hotspots"])
async def get_high_risk_hotspots():
    """
    Shortcut endpoint to retrieve critical and high risk tier hotspots.
    """
    res = hotspot_engine.list_hotspots(min_risk=70.0, page_size=50)
    return res.items


@router.get("/hotspots/bbox", response_model=List[HotspotSummarySchema], tags=["Hotspots"])
async def get_hotspots_bbox(
    min_lat: float = Query(..., description="Minimum latitude"),
    min_lon: float = Query(..., description="Minimum longitude"),
    max_lat: float = Query(..., description="Maximum latitude"),
    max_lon: float = Query(..., description="Maximum longitude")
):
    """
    Retrieve hotspots contained within or intersecting a bounding box.
    """
    return hotspot_engine.get_hotspots_in_bbox(min_lat, min_lon, max_lat, max_lon)


@router.get("/hotspots/nearby", response_model=List[HotspotSummarySchema], tags=["Hotspots"])
async def get_hotspots_nearby(
    latitude: float = Query(..., description="Target center latitude"),
    longitude: float = Query(..., description="Target center longitude"),
    radius_km: float = Query(500.0, ge=1.0, le=10000.0, description="Search radius in kilometers")
):
    """
    Retrieve hotspots within a geographic radius (km) of specified coordinate.
    """
    return hotspot_engine.get_nearby_hotspots(latitude, longitude, radius_km)


@router.get("/hotspots/{hotspot_id}", response_model=HotspotDetailSchema, tags=["Hotspots"])
async def get_hotspot_by_id(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Retrieve detailed scientific analysis, landcover context, and timeline for a specific hotspot.
    """
    detail = hotspot_engine.get_hotspot_detail(hotspot_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Hotspot '{hotspot_id}' not found.")
    return detail


@router.get("/hotspots/{hotspot_id}/history", response_model=List[HotspotSnapshotSchema], tags=["Hotspots"])
async def get_hotspot_history(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Retrieve historical timeline snapshots for FRP, event count, area, and risk score evolution.
    """
    detail = hotspot_engine.get_hotspot_detail(hotspot_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Hotspot '{hotspot_id}' not found.")
    return detail.timeline_snapshots


@router.get("/hotspots/{hotspot_id}/timeline", response_model=List[HotspotSnapshotSchema], tags=["Hotspots"])
async def get_hotspot_timeline(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Alias for /hotspots/{id}/history.
    """
    return await get_hotspot_history(hotspot_id)


# =====================================================================
# PHASE 11: INCIDENT RESPONSE, WIND, PLUME, EMERGENCY & PDF ENDPOINTS
# =====================================================================

from datetime import datetime, timezone
from fastapi.responses import Response
from app.schemas.hotspot import (
    WindDataSchema,
    PlumeConeResponse,
    EmergencyFacilitySchema,
    EmergencyContextResponse,
    IncidentIntelResponse
)
from app.services.weather_service import weather_service, plume_engine
from app.services.emergency_service import emergency_service
from app.services.pdf_report_service import pdf_report_service
from app.services.industrial_service import get_all_facilities


@router.get("/weather/wind", response_model=WindDataSchema, tags=["Weather"])
async def get_wind_data(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude degree"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude degree")
):
    """
    Retrieve current 10m wind conditions and 12-hour hourly forecasts with spatial grid caching.
    """
    return await weather_service.get_wind_data(latitude, longitude)


@router.get("/hotspots/{hotspot_id}/wind", response_model=WindDataSchema, tags=["Weather"])
async def get_hotspot_wind(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Retrieve real-time wind speed, direction, and hourly forecasts for a specific hotspot.
    """
    detail = hotspot_engine.get_hotspot_detail(hotspot_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Hotspot '{hotspot_id}' not found.")
    return await weather_service.get_wind_data(detail.centroid_lat, detail.centroid_lon)


@router.get("/hotspots/{hotspot_id}/plume", response_model=PlumeConeResponse, tags=["Weather"])
async def get_hotspot_plume(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Retrieve time-aware indicative screening-level plume transport polygons (1h, 3h, 6h, 12h horizons).
    """
    detail = hotspot_engine.get_hotspot_detail(hotspot_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Hotspot '{hotspot_id}' not found.")
    wind = await weather_service.get_wind_data(detail.centroid_lat, detail.centroid_lon)
    return plume_engine.generate_plume_cones(
        hotspot_id=detail.id,
        hotspot_name=detail.name,
        lat=detail.centroid_lat,
        lon=detail.centroid_lon,
        wind=wind
    )


@router.get("/emergency/nearby", response_model=List[EmergencyFacilitySchema], tags=["Emergency"])
async def get_emergency_nearby(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude degree"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude degree"),
    radius_km: float = Query(12.0, ge=1.0, le=50.0, description="Search radius in kilometers")
):
    """
    Retrieve nearby fire stations, hospitals, verified burn/trauma units, and fire hydrants from OpenStreetMap.
    """
    return await emergency_service.get_nearby_emergency_infrastructure(latitude, longitude, radius_km)


@router.get("/hotspots/{hotspot_id}/emergency-context", response_model=EmergencyContextResponse, tags=["Emergency"])
async def get_hotspot_emergency_context(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Evaluate nearest emergency resources and calculate 1 km & 3 km evacuation planning buffer intersections.
    """
    detail = hotspot_engine.get_hotspot_detail(hotspot_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Hotspot '{hotspot_id}' not found.")
    
    industrial_facilities = get_all_facilities()
    return await emergency_service.get_emergency_context_for_hotspot(
        hotspot_id=detail.id,
        hotspot_name=detail.name,
        lat=detail.centroid_lat,
        lon=detail.centroid_lon,
        nearby_industrial_facilities=industrial_facilities
    )


@router.get("/hotspots/{hotspot_id}/incident-intel", response_model=IncidentIntelResponse, tags=["Incident"])
async def get_hotspot_incident_intelligence(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Retrieve unified incident intelligence payload aggregating thermal telemetry, wind vector,
    indicative plume cones, emergency infrastructure, planning buffers, and AI summary.
    """
    detail = hotspot_engine.get_hotspot_detail(hotspot_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Hotspot '{hotspot_id}' not found.")
    
    wind = await weather_service.get_wind_data(detail.centroid_lat, detail.centroid_lon)
    plume = plume_engine.generate_plume_cones(detail.id, detail.name, detail.centroid_lat, detail.centroid_lon, wind)
    
    industrial_facilities = get_all_facilities()
    emergency = await emergency_service.get_emergency_context_for_hotspot(
        hotspot_id=detail.id,
        hotspot_name=detail.name,
        lat=detail.centroid_lat,
        lon=detail.centroid_lon,
        nearby_industrial_facilities=industrial_facilities
    )

    ai_summary = (
        f"• Thermal Profile: Active thermal hotspot '{detail.name}' observed with peak FRP of {detail.max_frp:.1f} MW and {detail.event_count} satellite detections.\n"
        f"• Atmospheric Vector: 10m wind at {wind.wind_speed_kmh} km/h from {wind.cardinal_direction} ({wind.wind_direction_deg:.0f}°) creates downwind transport bearing of {wind.downwind_bearing_deg:.1f}°.\n"
        f"• Planning Buffers: 1km planning buffer contains {emergency.buffer_1km.industrial_facilities_count} industrial sites and {emergency.buffer_1km.hydrants_count} hydrants. 3km planning buffer contains {emergency.buffer_3km.fire_stations_count} fire stations and {emergency.buffer_3km.hospitals_count} hospitals.\n"
        f"• Immediate Response Resource: Nearest fire station is {emergency.nearest_fire_station.name if emergency.nearest_fire_station else 'Local Fire Service'} ({emergency.nearest_fire_station.distance_m/1000.0:.2f} km) and nearest hospital is {emergency.nearest_hospital.name if emergency.nearest_hospital else 'Regional Medical Center'} ({emergency.nearest_hospital.distance_m/1000.0:.2f} km)."
    )

    return IncidentIntelResponse(
        hotspot=detail,
        wind=wind,
        plume=plume,
        emergency=emergency,
        ai_investigation_summary=ai_summary,
        generated_at=datetime.now(timezone.utc).isoformat()
    )


@router.get("/hotspots/{hotspot_id}/report/pdf", tags=["Incident"])
async def export_incident_pdf_report(hotspot_id: str = Path(..., description="Target Hotspot ID")):
    """
    Generate and download a professional 2-page Executive Incident Disaster Brief in PDF format.
    """
    incident_intel = await get_hotspot_incident_intelligence(hotspot_id)
    pdf_bytes = pdf_report_service.generate_incident_pdf(incident_intel)
    
    filename = f"fieryvision_incident_{hotspot_id.lower().replace('-', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/pdf"
        }
    )


