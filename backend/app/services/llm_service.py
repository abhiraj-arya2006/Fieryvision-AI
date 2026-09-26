import logging
import re
from typing import Dict, Any, Optional, Tuple
import httpx
from app.core.config import settings

logger = logging.getLogger("llm_service")

SYSTEM_PROMPT = (
    "You are FieryVision AI, an evidence-grounded thermal intelligence assistant. "
    "Only explain verified information supplied by the FieryVision backend. "
    "Never invent observations, facilities, coordinates, dates, classifications, "
    "confidence, anomaly scores, persistence, risk scores, causes, or incidents. "
    "Distinguish observed data from interpretation. "
    "If the supplied evidence is insufficient, explicitly say so. "
    "Always answer using concise bullet points. "
    "Never use long paragraphs. "
    "Normally provide no more than 4-5 bullets and keep the response under approximately 100 words. "
    "Do not begin with 'Certainly', 'Sure', or 'Of course'. "
    "Do not add a summary after the bullets."
)

import time

OLLAMA_MODEL = getattr(settings, "OLLAMA_MODEL", "qwen2.5:14b")

_OLLAMA_LAST_CHECK_TIME: float = 0.0
_OLLAMA_IS_ALIVE: bool = False
_OLLAMA_CHECK_INTERVAL_SECONDS: float = 30.0


async def _is_ollama_reachable(base_url: str) -> bool:
    """Fast liveness check for Ollama to avoid waiting on connection timeouts."""
    global _OLLAMA_LAST_CHECK_TIME, _OLLAMA_IS_ALIVE
    now = time.time()
    if not _OLLAMA_IS_ALIVE and (now - _OLLAMA_LAST_CHECK_TIME < _OLLAMA_CHECK_INTERVAL_SECONDS):
        return False

    url = base_url.replace("localhost", "127.0.0.1").rstrip("/")
    tags_endpoint = f"{url}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(1.0, connect=0.4)) as client:
            resp = await client.get(tags_endpoint)
            _OLLAMA_LAST_CHECK_TIME = now
            _OLLAMA_IS_ALIVE = (resp.status_code == 200)
            return _OLLAMA_IS_ALIVE
    except Exception:
        _OLLAMA_LAST_CHECK_TIME = now
        _OLLAMA_IS_ALIVE = False
        return False


async def _call_ollama(system: str, prompt: str) -> Tuple[Optional[str], bool]:
    """Call Ollama API if reachable; returns (text, success)."""
    ollama_url = settings.OLLAMA_BASE_URL.replace("localhost", "127.0.0.1").rstrip("/")
    if not await _is_ollama_reachable(ollama_url):
        return None, False

    api_endpoint = f"{ollama_url}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "system": system,
        "prompt": prompt,
        "stream": False
    }
    try:
        timeout = httpx.Timeout(15.0, connect=1.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(api_endpoint, json=payload)
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                if text:
                    return text, True
            elif response.status_code == 404:
                logger.info(f"Ollama model {OLLAMA_MODEL} not found on server.")
            else:
                logger.info(f"Ollama returned HTTP {response.status_code}")
    except Exception as e:
        logger.debug(f"Ollama/Qwen service error: {str(e)}")
    return None, False


def _generate_grounded_answer(question: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Intelligent Grounded NLP Engine:
    Answers user questions directly, grounded strictly in the verified spatial, thermal,
    and industrial investigation data.
    """
    ctx = context or {}
    q = (question or "").strip().lower()

    # Extract verified variables safely
    lat = ctx.get("latitude")
    lon = ctx.get("longitude")
    loc_str = f"({lat:.4f}, {lon:.4f})" if lat is not None and lon is not None else "Target location"

    inside_zone = ctx.get("inside_industrial_zone")
    fac_name = ctx.get("nearest_facility_name")
    fac_type = ctx.get("nearest_facility_type")
    dist_m = ctx.get("distance_to_facility_m")
    landcover = ctx.get("landcover") or "Unknown"
    risk_score = ctx.get("risk_score")
    priority = (ctx.get("priority") or "low").upper()
    classification = ctx.get("classification") or "unclassified"
    method = ctx.get("classification_method") or "evidence_based"

    temporal = ctx.get("temporal_summary") or {}
    persistence = temporal.get("persistence") or "Unknown"
    det_7d = temporal.get("detections_7d", 0)
    det_30d = temporal.get("detections_30d", 0)
    det_count = temporal.get("observation_count") or det_30d
    duration_hrs = temporal.get("event_duration_hours", 0)

    thermal_detected = ctx.get("thermal_activity_detected")
    anomalies_count = ctx.get("active_anomalies_count", 0)
    is_anomaly = ctx.get("is_anomaly") or ctx.get("anomaly_flag", False)
    anomaly_score = ctx.get("anomaly_score")
    evidence_list = ctx.get("evidence") or []

    dist_str = f"{int(dist_m)}m" if dist_m is not None else "unknown distance"

    # If context is completely empty (no coordinate analyzed yet)
    if lat is None and lon is None and not ctx:
        return (
            "- FieryVision AI monitors thermal anomalies and industrial fire risk across a 15 km buffer around Giaspura, Ludhiana (30.8756°N, 75.8985°E).\n"
            "- To analyze a specific coordinate, enter latitude and longitude above (or click a preset) and select 'Analyse Location'.\n"
            "- Once loaded, I can answer questions regarding industrial boundary status, nearest facilities, landcover, thermal power (FRP), persistence, and risk scores."
        )

    # 1. Industrial Zone / Boundary Query
    if any(k in q for k in ["industrial", "zone", "cluster", "boundary", "factory", "factories", "plant", "sector"]):
        if any(k in q for k in ["nearest", "which facility", "what facility", "closest", "what factory", "which factory", "how far"]):
            # Specific nearest facility query
            lines = [
                f"- Nearest Facility: {fac_name or 'None identified nearby'} ({fac_type or 'Industrial Unit'}).",
                f"- Distance: Approximately {dist_str} from {loc_str}.",
                f"- Industrial Zone Status: {'Inside the designated Giaspura industrial cluster' if inside_zone else 'Outside designated industrial boundaries'}.",
                f"- Land Cover: Classified as '{landcover}'."
            ]
            return "\n".join(lines)
        else:
            # Industrial zone status query
            status_text = "YES: this coordinate is INSIDE the designated industrial cluster boundary." if inside_zone else "NO: this coordinate is OUTSIDE the designated industrial zone."
            lines = [
                f"- Status: {status_text}",
                f"- Nearest Industrial Site: {fac_name or 'None recorded'} ({fac_type or 'General Industrial'}), located {dist_str} away.",
                f"- Surface Classification: ESA WorldCover indicates '{landcover}'.",
                f"- Operational Context: {'Higher likelihood of industrial process heat (furnaces, boilers, metalworks).' if inside_zone else 'Thermal events here typically correlate with biomass, open agricultural burning, or municipal waste.'}"
            ]
            return "\n".join(lines)

    # 2. Risk / Priority / Safety / Danger Query
    if any(k in q for k in ["risk", "priority", "safe", "danger", "dangerous", "threat", "hazard", "score", "level", "critical", "severity"]):
        score_val = f"{risk_score}/100" if risk_score is not None else "Calculated based on evidence"
        guideline = (
            "Immediate alert dispatch & visual verification recommended." if priority == "CRITICAL"
            else "Elevated monitoring priority with cross-sensor validation." if priority == "HIGH"
            else "Standard automated surveillance; monitor next satellite passes." if priority == "MODERATE"
            else "Low operational concern; routine background monitoring."
        )
        lines = [
            f"- Triage Priority: {priority} (Risk Score: {score_val}).",
            f"- Evaluation Method: Evaluated via {method}.",
            f"- Facility Exposure: Located {dist_str} from {fac_name or 'nearest facility'} ({'Inside' if inside_zone else 'Outside'} industrial zone).",
            f"- Operational Guideline: {guideline}"
        ]
        return "\n".join(lines)

    # 3. Facility & Infrastructure Query
    if any(k in q for k in ["facility", "factory", "plant", "mill", "building", "infrastructure", "company"]):
        lines = [
            f"- Nearest Facility: {fac_name or 'None identified within 5 km'} ({fac_type or 'Industrial site'}).",
            f"- Distance: {dist_str} from target coordinates.",
            f"- Zone Placement: {'Within designated industrial cluster' if inside_zone else 'Outside industrial perimeter'}.",
            f"- Landcover: {landcover}."
        ]
        return "\n".join(lines)

    # 4. Thermal Activity / Fire / Heat / Anomaly / Temperature Query
    if any(k in q for k in ["thermal", "fire", "heat", "hotspot", "frp", "temperature", "burn", "burning", "anomaly", "satellite", "radiant"]):
        state = "ACTIVE thermal heat emissions detected" if thermal_detected else "No active thermal hotspot currently observed"
        anom_desc = "Flagged as statistical thermal anomaly by Isolation Forest" if is_anomaly else "Within expected statistical baseline"
        lines = [
            f"- Thermal Status: {state} at {loc_str}.",
            f"- Active Anomaly Count: {anomalies_count} nearby satellite detection(s).",
            f"- Anomaly Score: {f'{anomaly_score:.3f}' if anomaly_score is not None else 'N/A'} ({anom_desc}).",
            f"- Persistence: Categorized as '{persistence}'."
        ]
        return "\n".join(lines)

    # 5. Persistence / Temporal Behavior Query
    if any(k in q for k in ["persistence", "duration", "how long", "recur", "history", "often", "transient", "persistent", "recurring", "frequency", "days", "hours"]):
        meaning = (
            "Indicates stationary, long-duration industrial heat (e.g. continuous furnace/boiler)." if persistence.lower() == "persistent"
            else "Intermittent thermal spikes indicating recurring operational cycles or repeated fires." if persistence.lower() == "recurring"
            else "Single-day or short-lived thermal event, typical of open burning or transient flare."
        )
        lines = [
            f"- Persistence Category: {persistence}.",
            f"- Detection Frequency: {det_7d} observation(s) in last 7 days; {det_30d} in last 30 days.",
            f"- Event Duration: Recorded span of ~{duration_hrs:.1f} hours.",
            f"- Behavioral Implication: {meaning}"
        ]
        return "\n".join(lines)

    # 6. Landcover / Terrain / Ground Query
    if any(k in q for k in ["landcover", "land cover", "terrain", "crop", "agriculture", "built-up", "built up", "forest", "surface", "soil", "vegetation"]):
        implication = (
            "Dense man-made structures, roofs, roads, and industrial yards." if "built" in landcover.lower()
            else "Cultivated fields prone to seasonal crop residue (stubble) burning." if "crop" in landcover.lower()
            else "Natural or open vegetative cover." if "tree" in landcover.lower() or "grass" in landcover.lower()
            else "Standard regional terrain surface."
        )
        lines = [
            f"- ESA WorldCover Class: {landcover}.",
            f"- Resolution: 10-meter Sentinel optical & radar classification.",
            f"- Surface Implication: {implication}",
            f"- Zone Context: {'Inside industrial corridor' if inside_zone else 'Outside industrial corridor'}."
        ]
        return "\n".join(lines)

    # 7. Evidence / Audit Trail Query
    if any(k in q for k in ["evidence", "proof", "findings", "log", "why", "basis", "how do you know", "reason"]):
        evidence_lines = [f"- Evidence: {ev}" for ev in evidence_list[:3]] if evidence_list else [f"- Evidence: Classification established via {method}."]
        lines = [
            f"- Assessment: Classified as '{classification}' (Priority: {priority}).",
            *evidence_lines,
            f"- Data Grounding: Grounded in NASA VIIRS thermal passes, ESA WorldCover, and Giaspura industrial GIS."
        ]
        return "\n".join(lines)

    # 8. Action / Recommendation Query
    if any(k in q for k in ["action", "recommend", "protocol", "what should", "what to do", "respond", "inspect", "dispatch"]):
        rec = (
            "Dispatch rapid field response unit; verify factory fire safety systems immediately." if priority == "CRITICAL"
            else "Deploy drone visual inspection and alert local industrial fire safety officers." if priority == "HIGH"
            else "Log incident and monitor next scheduled NOAA-20/21 satellite overpass." if priority == "MODERATE"
            else "Standard automated baseline logging; no urgent dispatch required."
        )
        lines = [
            f"- Current Priority Tier: {priority} (Risk Score: {risk_score if risk_score is not None else 'N/A'}/100).",
            f"- Recommended Response: {rec}",
            f"- Nearest Facility Contact: {fac_name or 'N/A'} ({dist_str}).",
            "- Safety Note: Remote sensing provides decision support; follow official civil defense fire protocols."
        ]
        return "\n".join(lines)

    # 9. General Summary / Location Overview / Fallback
    lines = [
        f"- Target Coordinates: {loc_str} ({'Inside' if inside_zone else 'Outside'} industrial zone).",
        f"- Risk & Priority: Score {risk_score if risk_score is not None else 0}/100 · Tier: {priority}.",
        f"- Nearest Facility: {fac_name or 'None nearby'} ({dist_str}; type: {fac_type or 'Industrial'}).",
        f"- Landcover & Persistence: '{landcover}' with '{persistence}' thermal behavior."
    ]
    return "\n".join(lines)


async def generate_explanation(analysis_data: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Pass verified backend facts to Qwen for a structured bullet-point AI assessment.
    Falls back gracefully to intelligent grounded synthesis if Ollama is unavailable.
    Returns (explanation_text, is_llm_available).
    """
    event_id = analysis_data.get("event_id", "Location Investigation")
    lat = analysis_data.get("latitude")
    lon = analysis_data.get("longitude")
    classification = analysis_data.get("classification", "unclassified")
    method = analysis_data.get("classification_method", "evidence_based")
    risk_score = analysis_data.get("risk_score", 0.0)
    priority = (analysis_data.get("priority") or "low").upper()
    facility = analysis_data.get("nearest_facility_name", "None nearby")
    facility_dist = analysis_data.get("distance_to_facility_m")
    landcover = analysis_data.get("landcover", "Unknown")
    inside_zone = analysis_data.get("inside_industrial_zone", False)
    evidence_list = analysis_data.get("evidence", [])

    dist_str = f"{int(facility_dist)}m" if facility_dist is not None else "unknown"
    evidence_str = "; ".join(evidence_list) if evidence_list else "No evidence recorded"

    prompt = (
        f"VERIFIED BACKEND FACTS:\n"
        f"- Target ID: {event_id}\n"
        f"- Location: Lat {lat}, Lon {lon}\n"
        f"- Classification: {classification} (Method: {method})\n"
        f"- Risk Score: {risk_score}/100 | Priority: {priority}\n"
        f"- Nearest Industrial Facility: {facility} (Distance: {dist_str})\n"
        f"- Inside Industrial Zone: {inside_zone}\n"
        f"- Landcover Context: {landcover}\n"
        f"- Key Evidence: {evidence_str}\n\n"
        f"Summarise only the above verified facts in 3-5 bullet points using the form:\n"
        f"- Finding: ...\n"
        f"- Context: ...\n"
        f"- Risk/Significance: ...\n"
        f"- Directive: ...\n"
        f"Do not invent anything not listed above."
    )

    text, ok = await _call_ollama(SYSTEM_PROMPT, prompt)
    if ok and text:
        return text, True

    # High-quality deterministic grounded explanation
    finding_summary = (
        f"Active industrial heat signature identified at ({lat:.4f}, {lon:.4f})"
        if inside_zone and risk_score >= 50
        else f"Spatial investigation at ({lat:.4f}, {lon:.4f}) classified as '{classification}'"
    )
    directive = (
        "High triage priority: recommend visual drone confirmation and facility alert."
        if priority in ("CRITICAL", "HIGH")
        else "Routine operational surveillance: maintain standard satellite tracking."
    )

    grounded_explanation = (
        f"- Finding: {finding_summary}.\n"
        f"- Context: Nearest industrial site '{facility}' at {dist_str} ({'Inside' if inside_zone else 'Outside'} industrial zone); landcover is {landcover}.\n"
        f"- Risk/Significance: Assessed at {risk_score}/100 ({priority} priority) via {method}.\n"
        f"- Directive: {directive}"
    )
    return grounded_explanation, False


async def generate_chat_response(question: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, bool]:
    """
    Answer a user free-form question grounded strictly in the provided investigation context.
    Attempts local Ollama first; if unavailable, uses the grounded NLP answering engine.
    Returns (response_text, is_llm_available).
    """
    ctx = context or {}
    chat_system = (
        "You are FieryVision AI, an evidence-grounded thermal intelligence assistant. "
        "Only explain verified information supplied by the FieryVision backend. "
        "Never invent observations, facilities, coordinates, dates, classifications, "
        "confidence, anomaly scores, persistence, risk scores, causes, or incidents. "
        "If the supplied evidence is insufficient, say: "
        "'Insufficient evidence in the current FieryVision data.' "
        "Always answer using concise bullet points only. "
        "Never use long paragraphs. "
        "Normally provide no more than 4-5 bullets and keep the response under approximately 100 words. "
        "Do not begin with 'Certainly', 'Sure', or 'Of course'. "
        "Do not repeat the question. "
        "Do not add a summary after the bullets. "
        "Do not use markdown tables."
    )

    # Build context string for Ollama prompt
    ctx_lines = []
    if ctx.get("latitude") is not None:
        ctx_lines.append(f"Location: ({ctx['latitude']}, {ctx['longitude']})")
    if ctx.get("classification"):
        ctx_lines.append(f"Classification: {ctx['classification']} (method: {ctx.get('classification_method', 'unknown')})")
    if ctx.get("risk_score") is not None:
        ctx_lines.append(f"Risk Score: {ctx['risk_score']}/100, Priority: {ctx.get('priority', 'unknown')}")
    if ctx.get("nearest_facility_name"):
        dist = ctx.get("distance_to_facility_m")
        dist_str = f"{int(dist)}m" if dist is not None else "unknown distance"
        ctx_lines.append(f"Nearest Facility: {ctx['nearest_facility_name']} ({dist_str}, type: {ctx.get('nearest_facility_type', 'industrial')})")
    if ctx.get("inside_industrial_zone") is not None:
        ctx_lines.append(f"Inside Industrial Zone: {ctx['inside_industrial_zone']}")
    if ctx.get("landcover"):
        ctx_lines.append(f"Land Cover: {ctx['landcover']}")
    temporal = ctx.get("temporal_summary", {})
    if temporal.get("persistence"):
        ctx_lines.append(f"Persistence: {temporal['persistence']}")
    if ctx.get("thermal_activity_detected") is not None:
        ctx_lines.append(f"Thermal Activity Detected: {ctx['thermal_activity_detected']}")
    if ctx.get("active_anomalies_count") is not None:
        ctx_lines.append(f"Nearby Thermal Events: {ctx['active_anomalies_count']}")
    evidence = ctx.get("evidence", [])
    if evidence:
        ctx_lines.append(f"Evidence: {'; '.join(evidence)}")

    context_str = "\n".join(ctx_lines) if ctx_lines else "No investigation context available."

    prompt = (
        f"CURRENT FIERYVISION INVESTIGATION CONTEXT:\n"
        f"{context_str}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"Answer using only the above verified facts. "
        f"Use bullet points only (3-5 bullets max, under ~100 words)."
    )

    # 1. Try local Ollama if running
    text, ok = await _call_ollama(chat_system, prompt)
    if ok and text:
        return text, True

    # 2. Use Intelligent Grounded Q&A Engine
    grounded_answer = _generate_grounded_answer(question, ctx)
    return grounded_answer, False
