"""
Targeted Tests for FieryVision AI — FIRMS Data Pipeline & Temporal Intelligence.
Validates all 8 acceptance testing areas:
1. FIRMS schema normalization
2. Coordinate validation
3. Giaspura 50 km filtering
4. Spatial-temporal clustering
5. 7-day/30-day aggregation
6. Unique detection day calculation
7. Persistence classification
8. Graceful empty-data handling
"""

import io
import unittest
from datetime import datetime
import pandas as pd

from data_processing.config import (
    GEO_CONFIG,
    CLUSTERING_CONFIG,
    PERSISTENCE_CONFIG,
    PersistenceConfig,
)
from data_processing.geo.filter import (
    calculate_distance_km,
    calculate_distance_m,
    is_within_monitoring_area,
    filter_to_monitoring_area,
    get_bounding_box_for_radius,
)
from data_processing.firms.schemas import CANONICAL_FIRMS_COLUMNS, ClusteredEvent
from data_processing.firms.loader import (
    load_and_normalize_firms,
    validate_coordinates,
    normalize_acq_time,
    normalize_acq_date,
    normalize_confidence,
    generate_event_id,
)
from data_processing.firms.active_service import FIRMSActiveService
from data_processing.temporal.clustering import (
    cluster_firms_detections,
    aggregate_clusters_to_events,
    parse_detection_datetime,
)
from data_processing.temporal.persistence import (
    classify_persistence,
    compute_event_temporal_features,
    analyze_events_persistence,
)
from data_processing.pipeline import FIRMSTemporalPipeline


class TestFIRMSPipeline(unittest.TestCase):
    """Comprehensive test suite for FIRMS and Temporal modules."""

    def setUp(self):
        # Sample VIIRS NRT raw CSV snippet (LANCE format)
        self.sample_viirs_csv = (
            "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n"
            "30.8756,75.8985,335.2,0.4,0.4,2026-09-14,1345,N20,n,2.0NRT,298.1,14.5,D\n"
            "30.8760,75.8990,340.1,0.4,0.4,2026-09-14,1345,N20,h,2.0NRT,301.2,18.2,D\n"
            "30.9120,75.8530,320.0,0.5,0.4,2026-09-14,0430,N21,l,2.0NRT,290.0,6.3,N\n"
        )

        # Sample MODIS format snippet
        self.sample_modis_csv = (
            "lat,lon,brightness,acq_date,acq_time,satellite,confidence,frp,daynight\n"
            "30.8750,75.8980,315.5,2026/09/14,430,Terra,85,12.0,N\n"
        )

    # =========================================================================
    # 1. FIRMS SCHEMA NORMALIZATION
    # =========================================================================
    def test_firms_schema_normalization_viirs(self):
        df = load_and_normalize_firms(self.sample_viirs_csv)
        
        # Verify canonical columns exist
        for col in CANONICAL_FIRMS_COLUMNS:
            self.assertIn(col, df.columns, f"Missing canonical column: {col}")
        
        self.assertEqual(len(df), 3)
        row0 = df.iloc[0]
        self.assertAlmostEqual(row0["latitude"], 30.8756, places=4)
        self.assertAlmostEqual(row0["longitude"], 75.8985, places=4)
        self.assertEqual(row0["acq_date"], "2026-09-14")
        self.assertEqual(row0["acq_time"], "1345")
        self.assertEqual(row0["confidence"], "nominal")  # 'n' normalized to 'nominal'
        self.assertEqual(row0["daynight"], "D")
        self.assertEqual(row0["frp"], 14.5)
        self.assertEqual(row0["brightness"], 335.2)
        self.assertTrue(row0["event_id"].startswith("FIRMS_N20_20260914_1345_"))

    def test_firms_schema_normalization_modis_and_formats(self):
        df = load_and_normalize_firms(self.sample_modis_csv)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["acq_date"], "2026-09-14")  # Slashes converted to hyphen ISO
        self.assertEqual(row["acq_time"], "0430")        # 430 padded to 0430
        self.assertEqual(row["confidence"], "high")       # 85% mapped to 'high'
        self.assertEqual(row["brightness"], 315.5)

    def test_event_id_determinism(self):
        id1 = generate_event_id("N20", "2026-09-14", "1345", 30.8756, 75.8985)
        id2 = generate_event_id("N20", "2026-09-14", "1345", 30.8756, 75.8985)
        self.assertEqual(id1, id2)
        self.assertIn("30.8756N_75.8985E", id1)

    # =========================================================================
    # 2. COORDINATE VALIDATION
    # =========================================================================
    def test_coordinate_validation(self):
        self.assertTrue(validate_coordinates(30.8756, 75.8985))
        self.assertTrue(validate_coordinates(0.0, 0.0))
        self.assertTrue(validate_coordinates(-90.0, -180.0))
        self.assertTrue(validate_coordinates(90.0, 180.0))

        self.assertFalse(validate_coordinates(91.0, 75.0))
        self.assertFalse(validate_coordinates(-95.0, 75.0))
        self.assertFalse(validate_coordinates(30.0, 185.0))
        self.assertFalse(validate_coordinates(30.0, -185.0))
        self.assertFalse(validate_coordinates("invalid", 75.0))
        self.assertFalse(validate_coordinates(float("nan"), 75.0))

    def test_invalid_coordinates_dropped_during_load(self):
        csv_with_bad_coords = (
            "latitude,longitude,acq_date,acq_time,frp,bright_ti4\n"
            "30.8756,75.8985,2026-09-14,1345,10.0,320.0\n"
            "999.0,75.8985,2026-09-14,1345,10.0,320.0\n"
            "30.8756,-250.0,2026-09-14,1345,10.0,320.0\n"
        )
        df = load_and_normalize_firms(csv_with_bad_coords)
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df.iloc[0]["latitude"], 30.8756)

    # =========================================================================
    # 3. GIASPURA 50 KM FILTERING
    # =========================================================================
    def test_giaspura_50km_filtering(self):
        center_lat = GEO_CONFIG.GIASPURA_LATITUDE   # 30.875625
        center_lon = GEO_CONFIG.GIASPURA_LONGITUDE  # 75.898481

        # Point 1: Giaspura focal point (~0.1 km)
        # Point 2: Khanna, Punjab (~37 km away, within 50 km)
        # Point 3: New Delhi (~285 km away, outside 50 km)
        records = [
            {"event_id": "P1", "latitude": 30.8760, "longitude": 75.8990, "acq_date": "2026-09-14", "acq_time": "1200"},
            {"event_id": "P2", "latitude": 30.7070, "longitude": 76.2200, "acq_date": "2026-09-14", "acq_time": "1200"},
            {"event_id": "P3", "latitude": 28.6139, "longitude": 77.2090, "acq_date": "2026-09-14", "acq_time": "1200"},
        ]
        df = pd.DataFrame(records)
        filtered = filter_to_monitoring_area(df, center_lat, center_lon, radius_km=50.0)

        self.assertEqual(len(filtered), 2)
        event_ids = filtered["event_id"].tolist()
        self.assertIn("P1", event_ids)
        self.assertIn("P2", event_ids)
        self.assertNotIn("P3", event_ids)

        # Verify distance column populated accurately
        p1_dist = filtered[filtered["event_id"] == "P1"]["distance_to_center_km"].iloc[0]
        self.assertLess(p1_dist, 1.0)

        p2_dist = filtered[filtered["event_id"] == "P2"]["distance_to_center_km"].iloc[0]
        self.assertTrue(30.0 < p2_dist < 45.0)

    def test_metric_distance_calculation(self):
        # Distance between Giaspura and Ludhiana Railway Station (~30.908, 75.856) is ~5.5 km
        dist_km = calculate_distance_km(30.875625, 75.898481, 30.9080, 75.8560)
        self.assertAlmostEqual(dist_km, 5.5, delta=1.0)
        dist_m = calculate_distance_m(30.875625, 75.898481, 30.9080, 75.8560)
        self.assertAlmostEqual(dist_m, dist_km * 1000.0, places=2)

    # =========================================================================
    # 4. SPATIAL-TEMPORAL CLUSTERING
    # =========================================================================
    def test_spatial_temporal_clustering(self):
        # Two points in Giaspura ~100m apart on same day (13:45 and 14:00) -> should cluster together
        # One point in Ludhiana ~5km away -> separate cluster
        data = [
            {"event_id": "E1", "latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-14", "acq_time": "1345", "frp": 12.0, "brightness": 320.0, "confidence": "nominal", "satellite": "N20"},
            {"event_id": "E2", "latitude": 30.8762, "longitude": 75.8990, "acq_date": "2026-09-14", "acq_time": "1400", "frp": 16.0, "brightness": 330.0, "confidence": "high", "satellite": "N20"},
            {"event_id": "E3", "latitude": 30.9100, "longitude": 75.8500, "acq_date": "2026-09-14", "acq_time": "1345", "frp": 8.0, "brightness": 310.0, "confidence": "low", "satellite": "N21"},
        ]
        df = pd.DataFrame(data)
        clustered_df = cluster_firms_detections(df, spatial_eps_meters=375.0, temporal_window_hours=24.0)
        
        # E1 and E2 should share cluster_id; E3 should have a different one
        c1 = clustered_df[clustered_df["event_id"] == "E1"]["cluster_id"].iloc[0]
        c2 = clustered_df[clustered_df["event_id"] == "E2"]["cluster_id"].iloc[0]
        c3 = clustered_df[clustered_df["event_id"] == "E3"]["cluster_id"].iloc[0]

        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)

        # Aggregate to events
        events = aggregate_clusters_to_events(clustered_df)
        self.assertEqual(len(events), 2)
        
        # Find the 2-detection event
        evt_main = next(e for e in events if e.detection_count == 2)
        self.assertEqual(evt_main.detection_count, 2)
        self.assertAlmostEqual(evt_main.average_frp, 14.0, places=1)
        self.assertEqual(evt_main.maximum_frp, 16.0)
        self.assertEqual(evt_main.confidence, "high")  # Aggregated high > nominal

    def test_clustering_time_window_separation(self):
        # Two points at the exact same location, but 48 hours apart -> should be separate clusters
        data = [
            {"event_id": "T1", "latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-10", "acq_time": "1200", "frp": 10.0, "brightness": 320.0, "confidence": "nominal", "satellite": "N20"},
            {"event_id": "T2", "latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-12", "acq_time": "1400", "frp": 15.0, "brightness": 325.0, "confidence": "nominal", "satellite": "N20"},
        ]
        df = pd.DataFrame(data)
        clustered = cluster_firms_detections(df, spatial_eps_meters=375.0, temporal_window_hours=24.0)
        c1 = clustered[clustered["event_id"] == "T1"]["cluster_id"].iloc[0]
        c2 = clustered[clustered["event_id"] == "T2"]["cluster_id"].iloc[0]
        self.assertNotEqual(c1, c2)

    # =========================================================================
    # 5. 7-DAY AND 30-DAY AGGREGATION
    # =========================================================================
    def test_seven_day_and_thirty_day_aggregation(self):
        # Event on 2026-09-30
        event = ClusteredEvent(
            cluster_id="EVENT_0001",
            latitude=30.8756,
            longitude=75.8985,
            first_seen="2026-09-30 12:00",
            last_seen="2026-09-30 12:00",
            duration_hours=0.0,
            detection_count=1,
            average_frp=10.0,
            maximum_frp=10.0,
            average_brightness=320.0,
            detections_7d=1,
            detections_30d=1,
            unique_detection_days=1,
            persistence="Transient",
            confidence="nominal",
            primary_satellite="N20",
        )

        # Historical detections at same spot:
        # Day 28 (within 7d): 2026-09-28
        # Day 20 (within 30d, outside 7d): 2026-09-20
        # Day 10 (within 30d, outside 7d): 2026-09-10
        # Day -40 (outside 30d): 2026-08-15
        hist_data = [
            {"latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-30", "acq_time": "1200", "frp": 10.0, "brightness": 320.0, "confidence": "n", "satellite": "N20", "daynight": "D"},
            {"latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-28", "acq_time": "1200", "frp": 12.0, "brightness": 322.0, "confidence": "n", "satellite": "N20", "daynight": "D"},
            {"latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-20", "acq_time": "1200", "frp": 14.0, "brightness": 325.0, "confidence": "n", "satellite": "N20", "daynight": "D"},
            {"latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-10", "acq_time": "1200", "frp": 16.0, "brightness": 330.0, "confidence": "n", "satellite": "N20", "daynight": "D"},
            {"latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-08-15", "acq_time": "1200", "frp": 25.0, "brightness": 350.0, "confidence": "h", "satellite": "N20", "daynight": "D"},
        ]
        df_hist = pd.DataFrame(hist_data)

        updated = compute_event_temporal_features(event, historical_df=df_hist, spatial_radius_m=375.0)

        # In 7 days (Sept 23 - Sept 30): Sept 28 and Sept 30 -> 2 detections
        self.assertEqual(updated.detections_7d, 2)
        # In 30 days (Aug 31 - Sept 30): Sept 10, 20, 28, 30 -> 4 detections (Aug 15 excluded)
        self.assertEqual(updated.detections_30d, 4)
        self.assertEqual(updated.unique_detection_days, 4)
        self.assertEqual(updated.persistence, "Recurring")  # 4 unique days is Recurring

    # =========================================================================
    # 6. UNIQUE DETECTION DAY CALCULATION
    # =========================================================================
    def test_unique_detection_day_calculation(self):
        # 3 detections on same date -> unique_detection_days == 1
        data_same_day = [
            {"event_id": "D1", "latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-14", "acq_time": "0400", "frp": 10.0, "brightness": 310.0, "confidence": "n", "satellite": "N20"},
            {"event_id": "D2", "latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-14", "acq_time": "1300", "frp": 12.0, "brightness": 315.0, "confidence": "n", "satellite": "N20"},
            {"event_id": "D3", "latitude": 30.8756, "longitude": 75.8985, "acq_date": "2026-09-14", "acq_time": "2200", "frp": 15.0, "brightness": 320.0, "confidence": "h", "satellite": "N20"},
        ]
        df_same = pd.DataFrame(data_same_day)
        clustered = cluster_firms_detections(df_same)
        events = aggregate_clusters_to_events(clustered)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].unique_detection_days, 1)

    # =========================================================================
    # 7. PERSISTENCE CLASSIFICATION
    # =========================================================================
    def test_persistence_classification(self):
        # Prototype specifications:
        # Transient: 1 unique detection day
        # Recurring: 2-4 unique detection days
        # Persistent: >= 5 unique detection days
        # Unknown: 0
        self.assertEqual(classify_persistence(1), "Transient")
        self.assertEqual(classify_persistence(2), "Recurring")
        self.assertEqual(classify_persistence(3), "Recurring")
        self.assertEqual(classify_persistence(4), "Recurring")
        self.assertEqual(classify_persistence(5), "Persistent")
        self.assertEqual(classify_persistence(15), "Persistent")
        self.assertEqual(classify_persistence(0), "Unknown")
        self.assertEqual(classify_persistence(-1), "Unknown")

    def test_persistence_custom_config(self):
        custom_cfg = PersistenceConfig(
            TRANSIENT_MAX_DAYS=2,
            RECURRING_MIN_DAYS=3,
            RECURRING_MAX_DAYS=6,
            PERSISTENT_MIN_DAYS=7,
        )
        self.assertEqual(classify_persistence(2, config=custom_cfg), "Transient")
        self.assertEqual(classify_persistence(5, config=custom_cfg), "Recurring")
        self.assertEqual(classify_persistence(7, config=custom_cfg), "Persistent")

    # =========================================================================
    # 8. GRACEFUL EMPTY-DATA HANDLING
    # =========================================================================
    def test_graceful_empty_data_handling(self):
        # Empty inputs must not crash any module
        empty_csv = ""
        df_empty = load_and_normalize_firms(empty_csv)
        self.assertTrue(df_empty.empty)
        for col in CANONICAL_FIRMS_COLUMNS:
            self.assertIn(col, df_empty.columns)

        filtered_empty = filter_to_monitoring_area(df_empty)
        self.assertTrue(filtered_empty.empty)

        clustered_empty = cluster_firms_detections(df_empty)
        self.assertTrue(clustered_empty.empty)

        events_empty = aggregate_clusters_to_events(clustered_empty)
        self.assertEqual(events_empty, [])

        # End-to-end pipeline empty handling
        pipeline = FIRMSTemporalPipeline()
        res = pipeline.process_observations("")
        self.assertEqual(res["events"], [])
        self.assertEqual(res["summary"]["total_clustered_events"], 0)

        # Active service missing key graceful handling
        svc = FIRMSActiveService(map_key="")
        df_active, meta = svc.fetch_for_giaspura()
        self.assertTrue(df_active.empty)
        self.assertEqual(meta["status"], "unavailable")
        self.assertEqual(meta["record_count"], 0)


if __name__ == "__main__":
    unittest.main()
