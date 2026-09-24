"""
NASA FIRMS historical and raw CSV loader, validator, and normalizer.
Adheres strictly to NASA LANCE / FIRMS data formats (VIIRS 375m & MODIS 1km).
"""

import hashlib
import os
import re
from datetime import datetime
from typing import Union, TextIO, Optional, List, Dict, Any
import pandas as pd

from data_processing.firms.schemas import CANONICAL_FIRMS_COLUMNS


def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate that coordinates fall within standard geographic bounds."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        return (-90.0 <= lat_f <= 90.0) and (-180.0 <= lon_f <= 180.0) and not (pd.isna(lat_f) or pd.isna(lon_f))
    except (TypeError, ValueError):
        return False


def normalize_acq_time(val: Any) -> str:
    """
    Normalize acquisition time string to 4-digit HHMM representation.
    Handles ints, floats, strings, and zero-padded times (e.g. 430 -> '0430').
    """
    if pd.isna(val) or val is None:
        return "0000"
    s = str(val).strip()
    # Remove decimal points if parsed as float e.g. 430.0 -> 430
    if "." in s:
        s = s.split(".")[0]
    # Remove non-digits
    digits = re.sub(r"\D", "", s)
    if not digits:
        return "0000"
    # Pad to 4 digits or truncate if > 4
    if len(digits) < 4:
        return digits.zfill(4)
    return digits[:4]


def normalize_acq_date(val: Any) -> Optional[str]:
    """
    Normalize acquisition date string to standard ISO 'YYYY-MM-DD'.
    Handles multiple date formats safely.
    """
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    # Try common formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y%m%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # If already matches YYYY-MM-DD regex
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    return None


def normalize_confidence(val: Any) -> str:
    """
    Normalize confidence levels.
    VIIRS: 'l' -> 'low', 'n' -> 'nominal', 'h' -> 'high'.
    MODIS: 0-100 percentage.
    """
    if pd.isna(val) or val is None:
        return "nominal"
    s = str(val).strip().lower()
    mapping = {
        "l": "low",
        "low": "low",
        "n": "nominal",
        "nominal": "nominal",
        "h": "high",
        "high": "high",
    }
    if s in mapping:
        return mapping[s]
    # If numeric percentage
    try:
        num = float(s)
        if num < 30:
            return "low"
        elif num < 80:
            return "nominal"
        else:
            return "high"
    except ValueError:
        return s


def generate_event_id(
    satellite: str,
    acq_date: str,
    acq_time: str,
    latitude: float,
    longitude: float,
) -> str:
    """Generate a deterministic and human-readable event_id for an observation."""
    lat_card = "N" if latitude >= 0 else "S"
    lon_card = "E" if longitude >= 0 else "W"
    coord_part = f"{abs(latitude):.4f}{lat_card}_{abs(longitude):.4f}{lon_card}"
    date_clean = acq_date.replace("-", "")
    time_clean = acq_time.replace(":", "")
    sat_clean = re.sub(r"[^A-Za-z0-9]", "", str(satellite)).upper() or "FIRMS"
    return f"FIRMS_{sat_clean}_{date_clean}_{time_clean}_{coord_part}"


def load_and_normalize_firms(
    source: Union[str, os.PathLike, TextIO, pd.DataFrame, List[Dict[str, Any]]]
) -> pd.DataFrame:
    """
    Load and normalize raw NASA FIRMS data into canonical FieryVision AI schema.
    
    Accepts:
      - File path (CSV)
      - TextIO / StringIO buffer
      - Existing pandas DataFrame
      - List of raw observation dictionaries
      
    Returns:
      pandas.DataFrame adhering to canonical columns and validation criteria.
    """
    if isinstance(source, pd.DataFrame):
        df_raw = source.copy()
    elif isinstance(source, list):
        if not source:
            return _create_empty_normalized_df()
        df_raw = pd.DataFrame(source)
    elif isinstance(source, (str, os.PathLike)) and os.path.exists(source):
        try:
            df_raw = pd.read_csv(source)
        except pd.errors.EmptyDataError:
            return _create_empty_normalized_df()
    elif hasattr(source, "read"):
        try:
            df_raw = pd.read_csv(source)
        except pd.errors.EmptyDataError:
            return _create_empty_normalized_df()
    elif isinstance(source, str) and ("\n" in source or "," in source):
        # String content buffer
        import io
        try:
            df_raw = pd.read_csv(io.StringIO(source))
        except pd.errors.EmptyDataError:
            return _create_empty_normalized_df()
    else:
        # File not found or empty
        return _create_empty_normalized_df()

    if df_raw.empty:
        return _create_empty_normalized_df()

    # Standardize column names to lower case and strip whitespace
    df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]

    # Column mappings for flexibility across VIIRS/MODIS feeds
    lat_col = next((c for c in ["latitude", "lat"] if c in df_raw.columns), None)
    lon_col = next((c for c in ["longitude", "lon", "long"] if c in df_raw.columns), None)
    date_col = next((c for c in ["acq_date", "date"] if c in df_raw.columns), None)
    time_col = next((c for c in ["acq_time", "time"] if c in df_raw.columns), None)
    frp_col = next((c for c in ["frp", "fire_radiant_power"] if c in df_raw.columns), None)
    bright_col = next((c for c in ["bright_ti4", "brightness", "bright_t31"] if c in df_raw.columns), None)
    conf_col = next((c for c in ["confidence", "conf"] if c in df_raw.columns), None)
    sat_col = next((c for c in ["satellite", "sat", "instrument"] if c in df_raw.columns), None)
    daynight_col = next((c for c in ["daynight", "day_night"] if c in df_raw.columns), None)
    id_col = next((c for c in ["event_id", "id", "detection_id"] if c in df_raw.columns), None)

    if lat_col is None or lon_col is None:
        raise ValueError("FIRMS data missing essential latitude/longitude columns.")

    records: List[Dict[str, Any]] = []

    for _, row in df_raw.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
        except (ValueError, TypeError):
            continue

        if not validate_coordinates(lat, lon):
            continue

        raw_date = row[date_col] if date_col else None
        acq_date = normalize_acq_date(raw_date)
        if not acq_date:
            continue

        raw_time = row[time_col] if time_col else "0000"
        acq_time = normalize_acq_time(raw_time)

        # FRP
        try:
            frp = float(row[frp_col]) if frp_col and not pd.isna(row[frp_col]) else 0.0
            frp = max(0.0, frp)
        except (ValueError, TypeError):
            frp = 0.0

        # Brightness
        try:
            brightness = float(row[bright_col]) if bright_col and not pd.isna(row[bright_col]) else 300.0
        except (ValueError, TypeError):
            brightness = 300.0

        # Confidence
        raw_conf = row[conf_col] if conf_col else "nominal"
        confidence = normalize_confidence(raw_conf)

        # Satellite
        satellite = str(row[sat_col]).strip() if sat_col and not pd.isna(row[sat_col]) else "VIIRS"

        # Day/Night
        daynight = str(row[daynight_col]).strip().upper() if daynight_col and not pd.isna(row[daynight_col]) else "D"
        if daynight not in ("D", "N"):
            daynight = "D"

        # Event ID
        if id_col and not pd.isna(row[id_col]) and str(row[id_col]).strip():
            event_id = str(row[id_col]).strip()
        else:
            event_id = generate_event_id(satellite, acq_date, acq_time, lat, lon)

        rec: Dict[str, Any] = {
            "event_id": event_id,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "acq_date": acq_date,
            "acq_time": acq_time,
            "frp": round(frp, 2),
            "brightness": round(brightness, 2),
            "confidence": confidence,
            "satellite": satellite,
            "daynight": daynight,
        }

        # Preserve optional source fields
        if "bright_ti5" in df_raw.columns and not pd.isna(row.get("bright_ti5")):
            try:
                rec["bright_ti5"] = round(float(row["bright_ti5"]), 2)
            except (ValueError, TypeError):
                pass
        if "scan" in df_raw.columns and not pd.isna(row.get("scan")):
            try:
                rec["scan"] = round(float(row["scan"]), 2)
            except (ValueError, TypeError):
                pass
        if "track" in df_raw.columns and not pd.isna(row.get("track")):
            try:
                rec["track"] = round(float(row["track"]), 2)
            except (ValueError, TypeError):
                pass
        if "version" in df_raw.columns and not pd.isna(row.get("version")):
            rec["version"] = str(row["version"]).strip()

        records.append(rec)

    if not records:
        return _create_empty_normalized_df()

    df_out = pd.DataFrame(records)
    # Deduplicate observations by (event_id) or (lat, lon, acq_date, acq_time, satellite)
    df_out = df_out.drop_duplicates(subset=["latitude", "longitude", "acq_date", "acq_time", "satellite"]).reset_index(drop=True)
    return df_out


def _create_empty_normalized_df() -> pd.DataFrame:
    """Create an empty DataFrame with canonical FIRMS schema."""
    dtypes = {
        "event_id": "object",
        "latitude": "float64",
        "longitude": "float64",
        "acq_date": "object",
        "acq_time": "object",
        "frp": "float64",
        "brightness": "float64",
        "confidence": "object",
        "satellite": "object",
        "daynight": "object",
    }
    df = pd.DataFrame({col: pd.Series(dtype=dt) for col, dt in dtypes.items()})
    return df
