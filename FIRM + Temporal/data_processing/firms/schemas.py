"""
Authoritative schemas and data contracts for FIRMS observations and event clusters.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


# Canonical field list required for normalized FIRMS observations
CANONICAL_FIRMS_COLUMNS = [
    "event_id",
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "frp",
    "brightness",
    "confidence",
    "satellite",
    "daynight",
]


@dataclass
class NormalizedObservation:
    """Normalized FIRMS thermal anomaly observation."""
    event_id: str
    latitude: float
    longitude: float
    acq_date: str          # YYYY-MM-DD
    acq_time: str          # HHMM
    frp: float             # MW
    brightness: float      # Kelvin
    confidence: str        # 'low', 'nominal', 'high', or percentage string
    satellite: str         # 'N20', 'N21', 'N', etc.
    daynight: str          # 'D' or 'N'
    
    # Preserved source-specific or computed fields
    bright_ti5: Optional[float] = None
    scan: Optional[float] = None
    track: Optional[float] = None
    version: Optional[str] = None
    distance_to_center_km: Optional[float] = None
    extra_attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        extra = d.pop("extra_attributes", {})
        if extra:
            d.update(extra)
        return d


@dataclass
class ClusteredEvent:
    """Aggregated fire event produced from spatial-temporal clustering."""
    cluster_id: str
    latitude: float               # Centroid latitude
    longitude: float              # Centroid longitude
    first_seen: str               # Earliest detection timestamp (YYYY-MM-DD or ISO)
    last_seen: str                # Latest detection timestamp (YYYY-MM-DD or ISO)
    duration_hours: float         # Span between first and last detection in hours
    detection_count: int          # Total detections clustered into this event
    average_frp: float            # Mean FRP (MW)
    maximum_frp: float            # Max FRP (MW)
    average_brightness: float     # Mean brightness (K)
    detections_7d: int            # Detections within 7 days of cluster's last seen
    detections_30d: int           # Detections within 30 days of cluster's last seen
    unique_detection_days: int    # Number of unique calendar days detected
    persistence: str              # 'Transient' | 'Recurring' | 'Persistent' | 'Unknown'
    confidence: str               # Aggregated confidence indicator
    primary_satellite: str        # Predominant satellite source
    distance_to_center_km: Optional[float] = None
    detection_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
