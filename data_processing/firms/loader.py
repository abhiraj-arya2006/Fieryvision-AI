"""FIRMS raw data inspection, cleaning, schema normalization, and regional filtering."""

import glob
import json
import os
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from .constants import GIASPURA_LAT, GIASPURA_LON, DEFAULT_REGION_RADIUS_KM


def haversine_distance_km(
    lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float
) -> np.ndarray:
    """Vectorized Haversine metric distance in kilometers."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return R * c


def inspect_raw_firms(
    raw_dir: str,
    output_report_path: Optional[str] = None
) -> Dict:
    """Inspect all FIRMS CSV files in raw_dir and generate an observed statistics report."""
    csv_files = sorted(glob.glob(os.path.join(raw_dir, "*.csv")))
    report = {
        "summary": {
            "files_inspected": len(csv_files),
            "file_names": [os.path.basename(f) for f in csv_files],
            "total_raw_rows": 0,
            "overall_date_range": None,
            "overall_coordinate_bounds": {}
        },
        "files": {}
    }

    all_lats, all_lons, all_dates = [], [], []

    for fpath in csv_files:
        fname = os.path.basename(fpath)
        df = pd.read_csv(fpath)
        rows = len(df)
        report["summary"]["total_raw_rows"] += rows

        cols = list(df.columns)
        missing_counts = df.isna().sum().to_dict()
        dup_count = int(df.duplicated().sum())

        date_min = str(df["acq_date"].min()) if "acq_date" in df else None
        date_max = str(df["acq_date"].max()) if "acq_date" in df else None
        lat_min = float(df["latitude"].min()) if "latitude" in df else None
        lat_max = float(df["latitude"].max()) if "latitude" in df else None
        lon_min = float(df["longitude"].min()) if "longitude" in df else None
        lon_max = float(df["longitude"].max()) if "longitude" in df else None

        satellites = df["satellite"].unique().tolist() if "satellite" in df else []
        confidence_vals = df["confidence"].unique().tolist() if "confidence" in df else []

        if "latitude" in df:
            all_lats.extend([lat_min, lat_max])
        if "longitude" in df:
            all_lons.extend([lon_min, lon_max])
        if "acq_date" in df:
            all_dates.extend([date_min, date_max])

        report["files"][fname] = {
            "rows": rows,
            "columns": cols,
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "date_range": [date_min, date_max],
            "lat_range": [lat_min, lat_max],
            "lon_range": [lon_min, lon_max],
            "satellites": [str(s) for s in satellites],
            "confidence_values": [str(c) for c in confidence_vals],
            "missing_values": missing_counts,
            "duplicate_rows": dup_count
        }

    if all_dates:
        report["summary"]["overall_date_range"] = [min(all_dates), max(all_dates)]
    if all_lats and all_lons:
        report["summary"]["overall_coordinate_bounds"] = {
            "lat_min": min(all_lats),
            "lat_max": max(all_lats),
            "lon_min": min(all_lons),
            "lon_max": max(all_lons)
        }

    if output_report_path:
        os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
        with open(output_report_path, "w", encoding="utf-8") as out:
            json.dump(report, out, indent=2)

    return report


def format_acq_time(t_val) -> str:
    """Format FIRMS acq_time (e.g., 740 -> '07:40', 1935 -> '19:35')."""
    s = str(t_val).strip()
    # remove decimal if float
    if "." in s:
        s = s.split(".")[0]
    s = s.zfill(4)
    if len(s) >= 4:
        return f"{s[:2]}:{s[2:4]}"
    return "00:00"


def normalize_satellite(sat_val) -> str:
    """Map FIRMS satellite codes to standard names."""
    s = str(sat_val).strip()
    mapping = {
        "1": "NOAA-20",
        "2": "NOAA-21",
        "N20": "NOAA-20",
        "N21": "NOAA-21",
        "N": "Suomi-NPP",
        "SNPP": "Suomi-NPP",
        "A": "Aqua",
        "T": "Terra"
    }
    return mapping.get(s, f"Satellite-{s}")


def normalize_confidence(conf_val) -> Tuple[str, float]:
    """Normalize confidence string/score: 'l'->('low', 0.3), 'n'->('nominal', 0.7), 'h'->('high', 1.0)."""
    s = str(conf_val).strip().lower()
    if s in ("h", "high"):
        return "high", 1.0
    if s in ("n", "nominal"):
        return "nominal", 0.7
    if s in ("l", "low"):
        return "low", 0.3
    try:
        score = float(s)
        if score > 80:
            return "high", 1.0
        elif score > 30:
            return "nominal", 0.7
        else:
            return "low", 0.3
    except ValueError:
        return "nominal", 0.7


def load_and_clean_firms(
    raw_dir: str,
    output_clean_csv: Optional[str] = None,
    filter_radius_km: float = DEFAULT_REGION_RADIUS_KM,
    center_lat: float = GIASPURA_LAT,
    center_lon: float = GIASPURA_LON
) -> pd.DataFrame:
    """Load, standardize schema, clean, filter regionally, and return normalized FIRMS observations."""
    csv_files = sorted(glob.glob(os.path.join(raw_dir, "*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No FIRMS CSV files found in {raw_dir}")

    dfs = []
    for f in csv_files:
        df = pd.read_csv(f)
        df["source_file"] = os.path.basename(f)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)

    # 1. Coordinate Validation
    combined = combined.dropna(subset=["latitude", "longitude"])
    combined["latitude"] = pd.to_numeric(combined["latitude"], errors="coerce")
    combined["longitude"] = pd.to_numeric(combined["longitude"], errors="coerce")
    combined = combined.dropna(subset=["latitude", "longitude"])
    valid_coords = (
        (combined["latitude"] >= -90.0) & (combined["latitude"] <= 90.0) &
        (combined["longitude"] >= -180.0) & (combined["longitude"] <= 180.0)
    )
    combined = combined[valid_coords].copy()

    # 2. Date and Time parsing
    combined["acq_date"] = pd.to_datetime(combined["acq_date"], errors="coerce")
    combined = combined.dropna(subset=["acq_date"])

    time_str = combined["acq_time"].apply(format_acq_time)
    combined["acq_time_str"] = time_str
    combined["timestamp"] = pd.to_datetime(
        combined["acq_date"].dt.strftime("%Y-%m-%d") + " " + combined["acq_time_str"],
        errors="coerce"
    )

    # 3. Numeric conversions for thermal features
    combined["brightness"] = pd.to_numeric(combined.get("brightness", combined.get("bright_ti4", np.nan)), errors="coerce")
    combined["bright_t31"] = pd.to_numeric(combined.get("bright_t31", np.nan), errors="coerce")
    combined["frp"] = pd.to_numeric(combined.get("frp", np.nan), errors="coerce")
    combined["scan"] = pd.to_numeric(combined.get("scan", np.nan), errors="coerce")
    combined["track"] = pd.to_numeric(combined.get("track", np.nan), errors="coerce")

    # Thermal difference (I4 - I5/T31) where available
    combined["ti4_ti5_diff"] = combined["brightness"] - combined["bright_t31"]

    # 4. Satellite and Confidence normalization
    combined["satellite"] = combined["satellite"].apply(normalize_satellite)
    conf_tuples = combined["confidence"].apply(normalize_confidence)
    combined["confidence_level"] = [t[0] for t in conf_tuples]
    combined["confidence_score"] = [t[1] for t in conf_tuples]

    # 5. Day/Night normalization
    if "daynight" in combined.columns:
        combined["daynight"] = combined["daynight"].astype(str).str.upper()
    else:
        combined["daynight"] = "UNKNOWN"

    # 6. Duplicate handling (same satellite, coordinate, timestamp)
    dup_cols = ["latitude", "longitude", "timestamp", "satellite"]
    combined = combined.drop_duplicates(subset=dup_cols).copy()

    # 7. Giaspura Regional Metric Filter
    combined["dist_to_giaspura_km"] = haversine_distance_km(
        combined["latitude"].values,
        combined["longitude"].values,
        center_lat,
        center_lon
    )
    filtered = combined[combined["dist_to_giaspura_km"] <= filter_radius_km].copy()

    # Sort chronologically
    filtered = filtered.sort_values(by=["timestamp", "latitude", "longitude"]).reset_index(drop=True)

    if output_clean_csv:
        os.makedirs(os.path.dirname(output_clean_csv), exist_ok=True)
        filtered.to_csv(output_clean_csv, index=False)

    return filtered
