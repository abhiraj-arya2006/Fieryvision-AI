"""Transparent evidence-based source-context assessment engine."""

from typing import Dict, List, Optional, Any


class EvidenceAssessmentEngine:
    """Transparent evidence engine assessing thermal behavior from FIRMS data alone.

    Conforms strictly to project guidance:
    - Never infers industrial causality without verified industrial infrastructure context.
    - Operates with available FIRMS thermal and temporal metrics.
    - Provides optional hooks for future industrial_context and landcover_context injection.
    """

    def __init__(
        self,
        high_frp_threshold: float = 40.0,
        moderate_frp_threshold: float = 20.0
    ):
        self.high_frp_threshold = high_frp_threshold
        self.moderate_frp_threshold = moderate_frp_threshold

    def evaluate_event(
        self,
        event: Dict[str, Any],
        industrial_context: Optional[Dict[str, Any]] = None,
        landcover_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate a thermal event cluster and produce transparent evidence output.

        Parameters:
            event: Dict containing event-level metrics.
            industrial_context: Optional future hook for OSM/industrial proximity.
            landcover_context: Optional future hook for ESA WorldCover classification.
        """
        evidence: List[str] = []
        limitations: List[str] = []

        max_frp = float(event.get("max_frp", 0.0) or 0.0)
        mean_frp = float(event.get("mean_frp", 0.0) or 0.0)
        obs_count = int(event.get("observation_count", 1) or 1)
        unique_days = int(event.get("unique_detection_days", 1) or 1)
        duration_h = float(event.get("event_duration_hours", 0.0) or 0.0)
        persistence = str(event.get("persistence", "Transient"))
        anomaly_flag = bool(event.get("anomaly_flag", False))
        anomaly_score = float(event.get("anomaly_score", 0.0) or 0.0)
        conf_level = str(event.get("dominant_confidence", "nominal")).lower()

        # 1. Thermal intensity evidence
        if max_frp >= self.high_frp_threshold:
            evidence.append(f"High thermal radiative power observed (peak FRP: {max_frp:.1f} MW)")
        elif max_frp >= self.moderate_frp_threshold:
            evidence.append(f"Moderate thermal radiative power observed (peak FRP: {max_frp:.1f} MW)")
        else:
            evidence.append(f"Low-to-moderate thermal emission (peak FRP: {max_frp:.1f} MW)")

        # 2. Multi-observation & Persistence evidence
        if persistence == "Persistent":
            evidence.append(f"Long temporal persistence observed across {unique_days} distinct days ({duration_h:.1f}h span)")
        elif persistence == "Recurring":
            evidence.append(f"Recurring thermal activity detected across {unique_days} distinct days")
        elif obs_count > 1:
            evidence.append(f"Multiple satellite overpass detections ({obs_count} observations)")

        # 3. Detection confidence evidence
        if conf_level == "high":
            evidence.append("High satellite detection confidence reported by sensor algorithm")
        elif conf_level == "nominal":
            evidence.append("Nominal satellite detection confidence")

        # 4. Thermal behavior anomaly evidence
        if anomaly_flag or anomaly_score >= 0.55:
            evidence.append(f"Statistically anomalous thermal profile flagged (anomaly score: {anomaly_score:.2f})")

        # 5. Optional External Context Hooks (Handling presence or absence cleanly)
        if industrial_context is not None:
            prox = industrial_context.get("proximity_context")
            if prox:
                evidence.append(f"Geospatial context: {prox}")
        else:
            limitations.append(
                "Industrial infrastructure context not available in this processing stage; "
                "source attribution cannot be asserted."
            )

        if landcover_context is not None:
            lc = landcover_context.get("landcover")
            if lc:
                evidence.append(f"Land-cover context: {lc}")
        else:
            limitations.append(
                "Land-cover substrate context not supplied; "
                "surface type cannot be verified from thermal data alone."
            )

        limitations.append(
            "Satellite thermal detections reflect radiometric heat anomalies; "
            "they do not prove specific combustion cause without ground verification."
        )

        # 6. Synthesize Assessment and Evidence Strength
        if persistence == "Persistent":
            assessment = "Persistent Thermal Activity"
            strength = "HIGH"
        elif anomaly_flag:
            assessment = "Unusual Thermal Behaviour"
            strength = "HIGH" if max_frp >= self.high_frp_threshold else "MEDIUM"
        elif persistence == "Recurring":
            assessment = "Recurring Thermal Activity"
            strength = "MEDIUM"
        elif obs_count >= 1:
            assessment = "Thermal Activity Detected"
            strength = "MEDIUM" if max_frp >= self.moderate_frp_threshold else "LOW"
        else:
            assessment = "Insufficient Evidence for Source Attribution"
            strength = "LOW"

        return {
            "assessment": assessment,
            "evidence_strength": strength,
            "evidence": evidence,
            "assessment_limitations": limitations
        }


_DEFAULT_EVIDENCE_ENGINE: Optional[EvidenceAssessmentEngine] = None


def get_default_evidence_engine() -> EvidenceAssessmentEngine:
    global _DEFAULT_EVIDENCE_ENGINE
    if _DEFAULT_EVIDENCE_ENGINE is None:
        _DEFAULT_EVIDENCE_ENGINE = EvidenceAssessmentEngine()
    return _DEFAULT_EVIDENCE_ENGINE


def assess_event_evidence(
    event: Dict[str, Any],
    industrial_context: Optional[Dict[str, Any]] = None,
    landcover_context: Optional[Dict[str, Any]] = None,
    engine: Optional[EvidenceAssessmentEngine] = None
) -> Dict[str, Any]:
    eng = engine or get_default_evidence_engine()
    return eng.evaluate_event(event, industrial_context=industrial_context, landcover_context=landcover_context)
