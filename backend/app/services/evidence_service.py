from typing import Dict, Any, List, Optional, Tuple

def evaluate_evidence(
    lat: float,
    lon: float,
    nearest_facility: Optional[Dict[str, Any]],
    distance_to_facility_m: float,
    inside_industrial_zone: bool,
    landcover: str,
    temporal_summary: Dict[str, Any],
    frp: Optional[float] = None,
    daynight: Optional[str] = None,
    anomaly_score: Optional[float] = None,
    anomaly_flag: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Evaluate empirical spatial, temporal, land-cover, and ML anomaly evidence for thermal events in Giaspura.
    Enforces scientific integrity:
    - Never fabricates ground truth.
    - Never claims proximity proves causation.
    - Indicates classification_method = 'evidence_based' (since supervised ML weights are absent).
    """
    evidence_claims: List[str] = []
    risk_score = 10.0  # Baseline thermal presence score
    classification = "unclassified"
    priority = "low"
    classification_confidence: Optional[float] = None

    # 1. Proximity to Giaspura Industrial Facilities
    if inside_industrial_zone:
        if nearest_facility:
            fac_name = nearest_facility.get("name", "Industrial Facility")
            fac_type = nearest_facility.get("site_type", "Industrial")
            evidence_claims.append(
                f"Spatial proximity: Located within {int(distance_to_facility_m)}m of industrial facility '{fac_name}' ({fac_type}). Note: Spatial correlation does not confirm causation."
            )
        else:
            evidence_claims.append(
                f"Spatial proximity: Located within {int(distance_to_facility_m)}m of an industrial facility. Note: Spatial correlation does not confirm causation."
            )
        risk_score += 35.0
    elif distance_to_facility_m <= 1500.0:
        if nearest_facility:
            fac_name = nearest_facility.get("name", "Industrial Facility")
            evidence_claims.append(
                f"Moderate proximity: Situated {int(distance_to_facility_m)}m from industrial facility '{fac_name}'."
            )
        else:
            evidence_claims.append(
                f"Moderate proximity: Situated {int(distance_to_facility_m)}m from an industrial facility."
            )
        risk_score += 15.0

    # 2. Landcover context (ESA WorldCover 10m / Heuristic)
    evidence_claims.append(f"Landcover context: Classified as '{landcover}'.")
    if "Industrial" in landcover or "Built-up" in landcover:
        risk_score += 15.0

    # 3. Temporal Persistence & Recurrence
    persistence = temporal_summary.get("persistence", "single_observation")
    det_30d = temporal_summary.get("detections_30d", 0)

    if persistence in ["high_persistence", "recurrent_heat_source", "Persistent", "Recurring"]:
        evidence_claims.append(
            f"Temporal pattern: High persistence observed ({det_30d} detections in 30 days). Recurrent thermal signatures in industrial sectors indicate stationary heat emissions (e.g. furnaces, boilers, stack flaring)."
        )
        risk_score += 25.0
    elif persistence in ["moderate_persistence"]:
        evidence_claims.append("Temporal pattern: Multiple thermal detections recorded over past observations.")
        risk_score += 10.0
    else:
        evidence_claims.append("Temporal pattern: Single thermal observation recorded.")

    # 4. Fire Radiative Power (FRP) & Diurnal Signal
    if frp is not None:
        evidence_claims.append(f"Thermal intensity: Fire Radiative Power (FRP) measured at {frp} MW.")
        if frp >= 20.0:
            risk_score += 15.0
        elif frp >= 10.0:
            risk_score += 10.0

    if daynight == "N":
        evidence_claims.append("Diurnal signal: Nocturnal thermal anomaly detected (nighttime industrial thermal emission).")
        risk_score += 10.0

    # 5. ML-Based Thermal Anomaly Detection (Isolation Forest)
    if anomaly_flag:
        evidence_claims.append(
            f"ML Anomaly: Isolation Forest flagged statistical thermal anomaly (anomaly score: {round(anomaly_score or 0.0, 2)})."
        )
        risk_score += 10.0

    # Final Classification decision based on cumulative evidence
    risk_score = min(round(risk_score, 1), 100.0)

    is_ind_land = "Industrial" in landcover or "Built-up" in landcover
    is_agri_land = "Agricultural" in landcover or "Cropland" in landcover

    if inside_industrial_zone and (persistence in ["high_persistence", "recurrent_heat_source", "Persistent"] or (frp and frp >= 10.0)):
        classification = "industrial_heat_source"
        classification_confidence = round(min(risk_score / 100.0, 0.95), 2)
    elif inside_industrial_zone or is_ind_land:
        classification = "industrial_heat_source"
        classification_confidence = 0.65
    elif is_agri_land and persistence in ["single_observation", "transient", "Transient"]:
        classification = "agricultural_burning"
        classification_confidence = 0.60
    else:
        classification = "unclassified"
        classification_confidence = None

    # Standard Priority levels: Critical (>=85.0), High (>=65.0), Moderate (>=40.0), Low (<40.0)
    if risk_score >= 85.0:
        priority = "critical"
    elif risk_score >= 65.0:
        priority = "high"
    elif risk_score >= 40.0:
        priority = "moderate"
    else:
        priority = "low"

    return {
        "classification": classification,
        "classification_method": "evidence_based",  # Strict flag per requirement
        "classification_confidence": classification_confidence,
        "risk_score": risk_score,
        "priority": priority,
        "evidence": evidence_claims
    }
