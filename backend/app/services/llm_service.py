import logging
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

OLLAMA_MODEL = getattr(settings, "OLLAMA_MODEL", "qwen2.5:14b")


async def _call_ollama(system: str, prompt: str) -> Tuple[Optional[str], bool]:
    """Internal helper: call Ollama API and return (text, success)."""
    ollama_url = settings.OLLAMA_BASE_URL.rstrip("/")
    api_endpoint = f"{ollama_url}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "system": system,
        "prompt": prompt,
        "stream": False
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        logger.info(f"Ollama/Qwen service unreachable: {str(e)}")
    return None, False


async def generate_explanation(analysis_data: Dict[str, Any]) -> Tuple[Optional[str], bool]:
    """
    Pass verified backend facts to Qwen for a structured bullet-point AI assessment.
    Returns (explanation_text, is_llm_available).
    """
    event_id = analysis_data.get("event_id", "Location Investigation")
    lat = analysis_data.get("latitude")
    lon = analysis_data.get("longitude")
    classification = analysis_data.get("classification", "unclassified")
    method = analysis_data.get("classification_method", "evidence_based")
    risk_score = analysis_data.get("risk_score", 0.0)
    priority = analysis_data.get("priority", "low")
    facility = analysis_data.get("nearest_facility_name", "None nearby")
    facility_dist = analysis_data.get("distance_to_facility_m")
    landcover = analysis_data.get("landcover", "Unknown")
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
        f"- Landcover Context: {landcover}\n"
        f"- Key Evidence: {evidence_str}\n\n"
        f"Summarise only the above verified facts in 3-5 bullet points using the form:\n"
        f"- Finding: ...\n"
        f"- Evidence: ...\n"
        f"- Risk/Significance: ...\n"
        f"- Limitation: ...\n"
        f"Do not invent anything not listed above."
    )

    text, ok = await _call_ollama(SYSTEM_PROMPT, prompt)
    if ok:
        return text, True

    # Deterministic fallback when LLM is unavailable
    fallback = (
        f"- Finding: Event '{event_id}' at ({lat}, {lon}) — classification: {classification}.\n"
        f"- Risk: Score {risk_score}/100, priority: {priority} (method: {method}).\n"
        f"- Context: Nearest facility — {facility} ({dist_str}); land cover: {landcover}.\n"
        f"- Limitation: AI explanation service offline; structured empirical evidence returned directly."
    )
    return fallback, False


async def generate_chat_response(question: str, context: Dict[str, Any]) -> Tuple[Optional[str], bool]:
    """
    Answer a user free-form question grounded strictly in the provided investigation context.
    Returns (response_text, is_llm_available).
    """
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

    # Build context string from available verified facts only
    ctx_lines = []
    if context.get("latitude") is not None:
        ctx_lines.append(f"Location: ({context['latitude']}, {context['longitude']})")
    if context.get("classification"):
        ctx_lines.append(
            f"Classification: {context['classification']} "
            f"(method: {context.get('classification_method', 'unknown')})"
        )
    if context.get("risk_score") is not None:
        ctx_lines.append(
            f"Risk Score: {context['risk_score']}/100, Priority: {context.get('priority', 'unknown')}"
        )
    if context.get("nearest_facility_name"):
        dist = context.get("distance_to_facility_m")
        dist_str = f"{int(dist)}m" if dist is not None else "unknown distance"
        ctx_lines.append(f"Nearest Facility: {context['nearest_facility_name']} ({dist_str})")
    if context.get("inside_industrial_zone") is not None:
        ctx_lines.append(f"Inside Industrial Zone: {context['inside_industrial_zone']}")
    if context.get("landcover"):
        ctx_lines.append(f"Land Cover: {context['landcover']}")
    temporal = context.get("temporal_summary", {})
    if temporal.get("persistence"):
        ctx_lines.append(f"Persistence: {temporal['persistence']}")
    if context.get("thermal_activity_detected") is not None:
        ctx_lines.append(f"Thermal Activity Detected: {context['thermal_activity_detected']}")
    if context.get("active_anomalies_count") is not None:
        ctx_lines.append(f"Nearby Thermal Events: {context['active_anomalies_count']}")
    evidence = context.get("evidence", [])
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

    text, ok = await _call_ollama(chat_system, prompt)
    if ok:
        return text, True

    return "- AI explanation unavailable — Ollama/Qwen service is offline.", False
