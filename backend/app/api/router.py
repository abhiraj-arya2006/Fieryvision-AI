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
