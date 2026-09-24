"""Thermal event geospatial enrichment service combining industrial context and land-cover."""

from typing import Dict, Any, Optional
from .industrial_service import IndustrialContextService, get_default_industrial_service
from .landcover_service import LandCoverService, get_default_landcover_service
from .validators import validate_coordinates


def enrich_thermal_event(
    event: Dict[str, Any],
    industrial_svc: Optional[IndustrialContextService] = None,
    landcover_svc: Optional[LandCoverService] = None
) -> Dict[str, Any]:
    """Enrich a thermal event record with industrial context and land-cover classification.

    Input record:
        {
            "latitude": float,
            "longitude": float,
            ... (optional other fields)
        }

    Output record contains:
        {
            "nearest_facility_name": str or None,
            "nearest_facility_type": str or None,
            "distance_to_facility_m": float or None,
            "inside_industrial_zone": bool,
            "distance_to_nearest_industrial_zone": float or None,
            "industrial_density_5km": int,
            "landcover": str,
            ... (preserves original fields)
        }
    """
    if "latitude" not in event or "longitude" not in event:
        raise KeyError("Thermal event must contain 'latitude' and 'longitude' fields.")

    lat, lon = validate_coordinates(event["latitude"], event["longitude"])

    ind_svc = industrial_svc or get_default_industrial_service()
    lc_svc = landcover_svc or get_default_landcover_service()

    ind_ctx = ind_svc.get_industrial_context(lat, lon)
    lc_class = lc_svc.get_landcover_class(lat, lon)

    # Build enriched result copying all original keys and adding enriched features
    enriched = dict(event)
    enriched.update({
        "nearest_facility_name": ind_ctx["nearest_facility_name"],
        "nearest_facility_type": ind_ctx["nearest_facility_type"],
        "distance_to_facility_m": ind_ctx["distance_to_facility_m"],
        "inside_industrial_zone": ind_ctx["inside_industrial_zone"],
        "distance_to_nearest_industrial_zone": ind_ctx["distance_to_nearest_industrial_zone"],
        "industrial_density_5km": ind_ctx["industrial_density_5km"],
        "landcover": lc_class,
        "proximity_context": ind_ctx.get("proximity_context", "")
    })

    return enriched
