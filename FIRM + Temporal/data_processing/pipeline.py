"""
End-to-End FIRMS and Temporal Intelligence Pipeline.
Coordinates data ingestion, geographic filtering, spatio-temporal clustering,
and temporal persistence analysis.
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import pandas as pd

from data_processing.config import (
    GEO_CONFIG,
    CLUSTERING_CONFIG,
    PERSISTENCE_CONFIG,
    GeoConfig,
    ClusteringConfig,
    PersistenceConfig,
)
from data_processing.geo.filter import filter_to_monitoring_area
from data_processing.firms.loader import load_and_normalize_firms, _create_empty_normalized_df
from data_processing.firms.schemas import ClusteredEvent
from data_processing.temporal.clustering import (
    cluster_firms_detections,
    aggregate_clusters_to_events,
)
from data_processing.temporal.persistence import analyze_events_persistence


class FIRMSTemporalPipeline:
    """
    End-to-end pipeline orchestrating FIRMS data processing,
    regional Giaspura filtering, clustering, and persistence analysis.
    """

    def __init__(
        self,
        geo_config: GeoConfig = GEO_CONFIG,
        clustering_config: ClusteringConfig = CLUSTERING_CONFIG,
        persistence_config: PersistenceConfig = PERSISTENCE_CONFIG,
        output_dir: Union[str, Path] = "data/processed",
    ):
        self.geo_config = geo_config
        self.clustering_config = clustering_config
        self.persistence_config = persistence_config
        self.output_dir = Path(output_dir)

    def process_observations(
        self,
        observations_source: Union[str, Path, pd.DataFrame, List[Dict[str, Any]]],
        historical_source: Optional[Union[str, Path, pd.DataFrame, List[Dict[str, Any]]]] = None,
        radius_km: Optional[float] = None,
        save_outputs: bool = False,
        output_prefix: str = "giaspura_fire_events",
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline from raw FIRMS observations to persistence-enriched events.
        
        Steps:
          1. Ingest & normalize observations to canonical schema.
          2. Filter to regional monitoring radius around Giaspura.
          3. Spatio-temporally cluster nearby detections (DBSCAN).
          4. Aggregate to event-level objects (centroids, FRP, duration).
          5. Compute 7d/30d temporal metrics and persistence classification.
          6. Optionally export processed results to JSON/GeoJSON.
          
        Returns:
          Dictionary containing:
            - 'events': List[ClusteredEvent]
            - 'events_df': pd.DataFrame
            - 'observations_df': pd.DataFrame (filtered & clustered)
            - 'summary': Dict with counts and persistence distribution
        """
        r_km = radius_km if radius_km is not None else self.geo_config.DEFAULT_MONITORING_RADIUS_KM

        # Step 1: Ingest & Normalize
        df_norm = load_and_normalize_firms(observations_source)
        if df_norm.empty:
            return self._empty_result()

        # Step 2: Geographic filtering
        df_geo = filter_to_monitoring_area(
            df_norm,
            center_lat=self.geo_config.GIASPURA_LATITUDE,
            center_lon=self.geo_config.GIASPURA_LONGITUDE,
            radius_km=r_km,
        )
        if df_geo.empty:
            return self._empty_result(total_raw_observations=len(df_norm))

        # Step 3: Spatio-temporal clustering
        df_clustered = cluster_firms_detections(
            df_geo,
            spatial_eps_meters=self.clustering_config.SPATIAL_EPS_METERS,
            temporal_window_hours=self.clustering_config.TEMPORAL_WINDOW_HOURS,
            min_samples=self.clustering_config.MIN_SAMPLES,
        )

        # Step 4: Event-level aggregation
        events = aggregate_clusters_to_events(
            df_clustered,
            center_lat=self.geo_config.GIASPURA_LATITUDE,
            center_lon=self.geo_config.GIASPURA_LONGITUDE,
        )

        # Step 5: Historical lookback & persistence classification
        df_hist = None
        if historical_source is not None:
            df_hist = load_and_normalize_firms(historical_source)

        enriched_events = analyze_events_persistence(
            events=events,
            historical_df=df_hist,
            spatial_radius_m=self.clustering_config.SPATIAL_EPS_METERS,
            config=self.persistence_config,
        )

        events_dicts = [e.to_dict() for e in enriched_events]
        events_df = pd.DataFrame(events_dicts) if events_dicts else pd.DataFrame()

        # Persistence distribution summary
        persist_counts = {}
        for e in enriched_events:
            persist_counts[e.persistence] = persist_counts.get(e.persistence, 0) + 1

        summary = {
            "total_raw_observations": len(df_norm),
            "observations_within_monitoring_area": len(df_geo),
            "total_clustered_events": len(enriched_events),
            "persistence_distribution": persist_counts,
            "center_coordinates": {
                "latitude": self.geo_config.GIASPURA_LATITUDE,
                "longitude": self.geo_config.GIASPURA_LONGITUDE,
            },
            "monitoring_radius_km": r_km,
        }

        # Step 6: Save outputs if requested
        if save_outputs:
            self._save_results(enriched_events, events_df, df_clustered, output_prefix)

        return {
            "events": enriched_events,
            "events_df": events_df,
            "observations_df": df_clustered,
            "summary": summary,
        }

    def _save_results(
        self,
        events: List[ClusteredEvent],
        events_df: pd.DataFrame,
        obs_df: pd.DataFrame,
        prefix: str,
    ) -> None:
        """Export output products to data/processed."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON events
        json_path = self.output_dir / f"{prefix}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in events], f, indent=2)

        # Save GeoJSON FeatureCollection
        geojson_path = self.output_dir / f"{prefix}.geojson"
        features = []
        for e in events:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [e.longitude, e.latitude],
                },
                "properties": e.to_dict(),
            })
        geojson_doc = {
            "type": "FeatureCollection",
            "features": features,
        }
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_doc, f, indent=2)

        # Save CSV summary
        if not events_df.empty:
            csv_path = self.output_dir / f"{prefix}.csv"
            events_df.to_csv(csv_path, index=False)

    def _empty_result(self, total_raw_observations: int = 0) -> Dict[str, Any]:
        """Return clean empty structure when no detections are present."""
        return {
            "events": [],
            "events_df": pd.DataFrame(),
            "observations_df": _create_empty_normalized_df(),
            "summary": {
                "total_raw_observations": total_raw_observations,
                "observations_within_monitoring_area": 0,
                "total_clustered_events": 0,
                "persistence_distribution": {},
                "center_coordinates": {
                    "latitude": self.geo_config.GIASPURA_LATITUDE,
                    "longitude": self.geo_config.GIASPURA_LONGITUDE,
                },
                "monitoring_radius_km": self.geo_config.DEFAULT_MONITORING_RADIUS_KM,
            },
        }
