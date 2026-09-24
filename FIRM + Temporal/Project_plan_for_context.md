# FieryVision AI — Technical Implementation & Architecture Plan

**Project**: AI-Assisted Geospatial Monitoring & Investigation System
**Target Area**: Giaspura, Ludhiana, Punjab, India (primary operational/display area; configurable regional buffer for backend context)
**Context**: 3-Day Hackathon Prototype (Smart India Hackathon 2026)
**Guiding Principles**: Defensible geospatial science, strict supervised ML adherence, zero fabricated data, map-first UX, transparent uncertainty labeling, evidence-backed assessment, active/near-real-time monitoring, and clear separation between validated ML and non-ML evidence assessment.

## Product Vision

FieryVision AI must transform a satellite-detected thermal anomaly into an actionable investigation result.

The product must answer four questions:

1. **Where is the thermal anomaly?**
2. **What is most likely happening there?**
3. **Is the thermal activity transient, recurring, or persistent?**
4. **Does the event require attention?**

Core product flow:

```
DETECT -> UNDERSTAND -> ANALYSE -> CLASSIFY -> MONITOR -> PRIORITIZE -> ACT
```

The system must never present proximity, land cover, or thermal intensity as proof of causality. Use wording such as **Probable Industrial Fire**, **Probable Persistent Industrial Thermal Source**, **Probable Agricultural Burning**, **Probable Natural / Forest Fire**, or **Other / Unknown**.

---

## User Review Required

> [!IMPORTANT]
> **CRITICAL SUPERVISED ML STATUS: BLOCKED PENDING GENUINE GROUND-TRUTH LABELS**
> Per Non-Negotiable Requirement 1, the ML classifier MUST use **Supervised Learning ONLY** on a genuine, documented labeled dataset. Synthetic labels, heuristic labels, and pseudo-labeling are strictly prohibited.
> **Inspection result**: Our environment scan confirms that **no labeled ground-truth fire dataset** exists on the local system (FIRMS data provides only satellite radiometric readings like FRP and brightness, not ground-truth fire origin labels).
> **Action**: The ML Training stage will remain **strictly blocked** from training fake models. We will build the full ML pipeline architecture (feature extraction, data validation, train/val/test split, Random Forest baseline, XGBoost candidate, and metrics calculation), ready to execute the moment a legitimate labeled dataset is provided. In the interim, the system will transparently report the model state as uncalibrated/blocked and power risk and evidence scoring through our defensible geospatial and temporal engine.

> [!NOTE]
> **Exact Giaspura Coordinates Verified**
> Direct OpenStreetMap/Nominatim query confirms Giaspura center:
>
> * **Latitude**: `30.875625° N`
> * **Longitude**: `75.898481° E`
> * **Primary Projected CRS**: `EPSG:32643` (WGS 84 / UTM Zone 43N) for precise metric distance calculations (avoiding degree distortion).

---

## A. Current Repository & Environment Status

| Component               | Status                | Details                                                                                                                    |
| :---------------------- | :-------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| **Workspace Directory** | Uninitialized / Empty | Workspace path `c:\Users\ABHIRAJ ARYA\Desktop\SO IMP\3D WEB DESIGNS\New folder` (or dedicated `fieryvision-AI` directory). |
| **Python Environment**  | Installed             | Python 3.12.10 available.                                                                                                  |
| **Node.js Environment** | Installed             | Node.js v22.15.1 and npm available.                                                                                        |
| **Git Environment**     | Installed             | Git 2.49.0.windows.1 available.                                                                                            |
| **Local Data Files**    | None present          | No FIRMS CSVs, no local OSM dumps, and no labeled datasets exist in the current workspace.                                 |

---

## B. Available Data & Authoritative Schemas

### 1. NASA FIRMS (VIIRS NRT / Archive)

FIRMS provides active thermal anomaly observations. The schema adheres strictly to NASA LANCE / FIRMS format:

* `latitude` (float64): hot spot latitude (WGS84)
* `longitude` (float64): hot spot longitude (WGS84)
* `bright_ti4` (float64): VIIRS I-4 thermal channel brightness temperature (Kelvin)
* `scan` (float64): pixel scan angle
* `track` (float64): pixel track width
* `acq_date` (string `YYYY-MM-DD`): acquisition date
* `acq_time` (string `HHMM`): acquisition time (UTC)
* `satellite` (string): `N` (Suomi NPP), `N20` (NOAA-20), `N21` (NOAA-21)
* `confidence` (string/int): `nominal`, `low`, `high` (VIIRS) or `0–100` (MODIS)
* `version` (string): processing version
* `bright_ti5` (float64): VIIRS I-5 thermal channel brightness temperature (Kelvin)
* `frp` (float64): Fire Radiative Power in Megawatts (MW)
* `daynight` (string): `D` (Day) or `N` (Night)

### 2. OpenStreetMap (Industrial & Contextual Features)

Queried via Overpass API with local GeoJSON caching:

* Target tags: `landuse=industrial`, `industrial=*`, `building=industrial`, `man_made=works`, `power=plant`, `power=substation`, `amenity=fuel`, `storage=*`, `landuse=commercial`.
* Stored as GeoDataFrames with geometry (`Polygon`, `MultiPolygon`, `Point`), `name`, `facility_type`, `osm_id`.

### 3. Land Cover (Contextual Evidence)

* ESA WorldCover / Copernicus Global Land Cover or OSM landuse fallback.
* Standard classes: Built-up, Cropland, Tree cover, Shrubland, Grassland, Bare / sparse vegetation, Water bodies.

---

## C. Missing Data Dependencies & Plan

1. **Ground-Truth Labeled Dataset for ML Fire Classification**:

   * *Status*: **MISSING**.
   * *Requirement for Unblocking*: A CSV/Parquet file containing confirmed historical thermal events in/near Punjab or comparable regions with verified source labels:

     * Target Column: `source_class` (e.g., `Industrial Fire`, `Agricultural Burning`, `Natural / Forest Fire`, `Other / Unknown`).
     * Provenance: Verified field reports, official state pollution board (PPCB) records, or validated academic ground-truth fire datasets.
   * *Safe Hackathon Stance*: The pipeline will report ML as "Awaiting Labeled Ground Truth". It will NOT fake accuracy numbers.

2. **NASA FIRMS MAP_KEY**:

   * The backend uses environment variable `FIRMS_MAP_KEY`.
   * If no API key is provided, the backend falls back seamlessly to the FIRMS public NRT 24-hour/48-hour open CSV feeds for South Asia / India or sample historical verification sets without crashing.

---

## D. Geographic Scope & Analysis Scales

```
┌─────────────────────────────────────────────────────────────┐
│  A. Regional Monitoring Area: 50 km Radius                  │
│     Center: 30.8756° N, 75.8985° E (Giaspura)               │
│     Covers: Regional situational awareness, all anomalies  │
│                                                             │
│     ┌─────────────────────────────────────────────────┐     │
│     │  B. Industrial Context Search: 5 km Radius       │     │
│     │     Per anomaly local buffer: nearby facilities │     │
│     │     Inside vs outside industrial polygon       │     │
│     │                                                 │     │
│     │     ┌─────────────────────────────────────┐     │     │
│     │     │  C. Event Clustering: ~375 m        │     │     │
│     │     │     VIIRS pixel resolution scale    │     │     │
│     │     │     Combines multi-detections       │     │     │
│     │     └─────────────────────────────────────┘     │     │
│     └─────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

1. **A. Giaspura Primary Operational Area**:

   * Center: `(30.875625, 75.898481)`
   * The frontend must focus tightly on Giaspura and its defined study boundary.
   * A configurable surrounding buffer may be used internally for historical/context data, but must not become the primary visual scope.
   * Leaflet map loads centered on Giaspura with a clear study-area boundary.
2. **B. 5 km Anomaly Context Radius**:

   * Search radius around *each anomaly* in metric projection (`EPSG:32643`).
   * Distinguishes between:

     * Is hotspot strictly *inside* an industrial polygon? (`inside_industrial_zone = True`)
     * What is the *nearest facility*? (`nearest_facility_name`, `nearest_facility_type`, `distance_to_facility_m`)
     * What is the *nearest industrial zone*?
3. **C. ~375 m Spatial-Temporal Clustering**:

   * Based on the VIIRS 375m I-band nominal pixel resolution.
   * DBSCAN or spatial buffering (`eps = 375 m`, `time_window = 24 hrs`) to cluster duplicate detections from morning/evening passes.
   * Computes cluster statistics: `detections_7d`, `detections_30d`, `unique_detection_days`, `average_frp`, `maximum_frp`.

---

## E. ML Pipeline & Training Strategy (When Data Is Available)

When a genuine labeled dataset is supplied:

1. **Model Candidates**:

   * **Baseline**: `RandomForestClassifier(n_estimators=150, class_weight='balanced', random_state=42)`
   * **Challenger**: `XGBClassifier(n_estimators=200, scale_pos_weight=..., eval_metric='mlogloss')`
2. **Spatial-Temporal Leakage Prevention**:

   * Group/block split: Split at the *spatial-temporal cluster or site level* so that the same fire event or industrial facility does not have observations split across train and test folds.
3. **Engineered Features**:

   * Radiometric: `frp`, `bright_ti4`, `bright_ti5`, `ti4_ti5_diff`
   * Spatial/Contextual: `distance_to_industrial_m`, `inside_industrial_zone`, `landcover_code`, `industrial_density_5km`
   * Temporal: `is_night`, `month`, `hour`, `detections_30d`, `unique_detection_days`
4. **Evaluation**:

   * Stratified per-class Precision, Recall, F1-score, and Confusion Matrix (not just overall accuracy).
5. **Persistence Engine (Independent of Source Classification)**:

   * Evaluated as a temporal behavior:

     * `Transient`: Detected on 1 unique day within 30 days.
     * `Recurring`: Detected across 2–4 unique days over 30 days.
     * `Persistent`: Detected $\ge 5$ unique days over 30 days (consistent with industrial furnaces, brick kilns, or flaring).

---

## F. Evidence-Based Assessment & Risk / Priority Scoring

When supervised ML is unavailable because genuine labels are missing, the prototype must still provide an **Evidence-Based Assessment** using observed data.

This is NOT presented as a trained ML prediction.

Evidence may include:

* industrial proximity
* industrial-zone membership
* land-cover context
* FRP / thermal intensity
* FIRMS confidence
* historical recurrence / persistence
* facility context

The UI must display the assessment method clearly:

```
Classification Method:
Evidence-Based Assessment
```

When a genuine validated supervised model exists, the UI may display:

```
Classification Method:
ML Validated
```

Do not fabricate labels, predictions, or accuracy metrics.

### Risk & Priority Scoring Architecture

Priority is distinct from classification confidence:
\(\text{Priority Score} = w_{\text{FRP}} \cdot S_{\text{FRP}} + w_{\text{prox}} \cdot S_{\text{industrial\_prox}} + w_{\text{persist}} \cdot S_{\text{persistence}} + w_{\text{conf}} \cdot S_{\text{confidence}}\)

* **FRP Score ($S_{\text{FRP}}$)**: Normalized thermal output (higher MW = higher attention).
* **Industrial Proximity Score ($S_{\text{industrial_prox}}$)**: 1.0 if inside industrial polygon; decaying linearly up to 5,000 m.
* **Persistence Score ($S_{\text{persistence}}$)**: High for persistent hot spots near dense settlements.
* **Output Levels**:

  * `CRITICAL`: 85–100
  * `HIGH`: 65–84
  * `MODERATE`: 40–64
  * `LOW`: 0–39
* **Evidence Breakdown**: Each event produces human-readable bullet points explaining *why* the priority was assigned, without claiming causality.

---

## G. Canonical API Schema & Endpoints

### Canonical Event Schema

```json
{
  "event_id": "VIIRS_20260914_001",
  "latitude": 30.8765,
  "longitude": 75.8992,
  "acq_date": "2026-09-14",
  "acq_time": "1345",
  "frp": 14.8,
  "brightness": 328.4,
  "confidence": "nominal",
  "satellite": "N20",
  "daynight": "D",
  "nearest_facility_name": "Hero Cycles Industrial Complex",
  "nearest_facility_type": "factory",
  "distance_to_facility_m": 240.5,
  "inside_industrial_zone": true,
  "landcover": "built-up",
  "detections_7d": 3,
  "detections_30d": 8,
  "unique_detection_days": 5,
  "average_frp": 12.2,
  "maximum_frp": 18.5,
  "first_seen": "2026-08-20",
  "last_seen": "2026-09-14",
  "persistence": "Persistent",
  "classification": "Probable Industrial Heat Source",
  "classification_confidence": 0.88,
  "risk_score": 82,
  "priority": "HIGH",
  "explanation_evidence": [
    "Located within designated industrial zone (Focal Point)",
    "240 m from mapped factory infrastructure",
    "Repeated thermal detections on 5 unique days in past 30 days (Persistent pattern)",
    "Thermal radiative power: 14.8 MW"
  ]
}
```

### Backend Endpoints

* `GET /api/health`: System health, active data sources, and ML model status.
* `GET /api/active-events`: Current FIRMS anomalies within 50 km Giaspura boundary.
* `GET /api/events/{event_id}`: Detailed event inspection.
* `GET /api/facilities`: Cached OSM industrial facilities and boundary polygons within the 50 km zone.
* `GET /api/statistics`: Summary counts by priority, persistence, and classification.
* `GET /api/map-data`: GeoJSON-ready map payload for the Giaspura frontend.
* `GET /api/satellite-context/{event_id}`: Returns satellite-context metadata or imagery access information where available.
* `POST /api/analyse-location`: Takes `{"latitude": float, "longitude": float}` and returns a complete evidence-backed on-demand investigation.

---

## H. Frontend Architecture (Lovable + React + Leaflet)

```
fieryvision-AI/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.jsx         # Full-screen Leaflet 50 km Giaspura map
│   │   │   ├── EventDrawer.jsx     # Side drawer for clicked event details
│   │   │   ├── FilterOverlay.jsx   # Compact filter & layer controls
│   │   │   ├── LegendOverlay.jsx   # Compact marker & priority legend
│   │   │   ├── AssistantPage.jsx   # Page 2: Coordinate AI investigation
│   │   │   └── Navbar.jsx          # Simple top switcher (Map View | AI Assistant)
│   │   ├── services/
│   │   │   └── api.js              # Axios/Fetch client for backend endpoints
│   │   └── App.jsx
```

### Key UI Features

1. **Map-First Entry (Page 1)**: Immediate interactive map focused on Giaspura (50 km monitoring circle). No generic landing hero banner.
2. **Zero-Event Scenario**: If FIRMS reports zero active hotspots, map renders cleanly with notification: *"No active thermal anomalies detected in the 50 km Giaspura radius over the past 24–48 hours."* Base layers, industrial boundaries, and historical inquiry remain functional.
3. **Event Marker Interaction**: Clicking an event opens a sleek sliding side-drawer presenting:

   * Thermal Anomaly Metrics (FRP, Satellite, Time)
   * Classification / Evidence Assessment + Method
   * Confidence only when supported by a validated model; otherwise show `Not Available`
   * Temporal Persistence Status
   * OpenStreetMap Proximity & Zone Status
   * Transparent Risk & Priority Score
   * Evidence Checklist
   * Satellite imagery/context view where available
4. **AI Assistant (Page 2)**: Input custom coordinates anywhere in the configured Giaspura study region for real-time spatial join, historical check, evidence-backed assessment, and human-readable explanation.
5. **Primary Navigation**: `Map View` and `AI Assistant`; the map is the default landing page.
6. **Data Status**: Clearly display whether results are `Active`, `Cached`, or `Historical`, plus a `Last Updated` timestamp.

---

## I. GenAI / Qwen Explanation Layer

This layer is optional until the core pipeline is stable, but should be supported in the architecture.

Use the existing local Qwen/Ollama capability if available.

The LLM receives ONLY structured evidence produced by the backend, for example:

* event classification or evidence assessment
* confidence, if available
* FRP
* industrial proximity
* land cover
* persistence
* risk / priority

The LLM must convert verified backend facts into a concise explanation. It must never invent:

* facilities
* thermal observations
* dates
* causes
* confidence values
* historical activity

The architecture is:

```
Coordinates / Selected Event
        |
        v
Backend Investigation
        |
        v
Structured Evidence
        |
        v
Qwen / LLM
        |
        v
Human-readable Explanation
```

## J. Satellite Evidence Layer

Use Sentinel-2 or another documented satellite imagery source primarily as a visual evidence/context layer.

The prototype does NOT require a deep-learning image classifier.

A selected event should allow the operator to inspect:

* hotspot location
* surrounding industrial / land-cover context
* available satellite imagery

Imagery must not be presented as proof of the exact cause of a thermal anomaly.

## K. Verification Plan

### Automated Tests

1. **Geospatial Projections**: Test distance calculation between known points in Ludhiana against geodesic formula (`geopy` / `pyproj` EPSG:32643).
2. **Giaspura Study-Area Filtering**: Confirm anomalies outside the configured primary study area are excluded from the primary view; internal backend context buffers must remain configurable.
3. **Event Clustering**: Verify that detections within 375m and 24h are correctly grouped into single events.
4. **OSM Context Extraction**: Verify that industrial polygons and point tags parse correctly without throwing coordinate swap errors.
5. **API Contract Tests**: Verify all FastAPI endpoints return expected HTTP status and adhere to canonical schema.
6. **Zero-Event Handling**: Verify API and UI gracefully handle empty event lists.

### Active Data Verification

1. Verify NASA FIRMS API connectivity when `FIRMS_MAP_KEY` is present.
2. Verify active-event timestamps and source mode are returned.
3. Verify fallback/cached mode is clearly labeled when live API access is unavailable.
4. Verify no frontend API key exposure.

### Manual Verification

1. Open frontend in browser: confirm map immediately centers on Giaspura with the configured study-area boundary.
2. Verify marker click interactions, filter toggles (by Priority, Classification, Persistence).
3. Test Page 2 with Giaspura coordinates `(30.8756, 75.8985)` and verify real spatial analysis returns in under 2 seconds.

# L. Implementation Priority for the 3-Day Prototype

Build in this exact order and keep each completed stage working:

1. **Active FIRMS ingestion -> Giaspura map**
2. **Lovable/React map UI + event drawer**
3. **Industrial infrastructure context**
4. **Land-cover context**
5. **Historical FIRMS + persistence**
6. **Evidence-Based Assessment**
7. **Risk / Priority scoring**
8. **Valid supervised ML, only if genuine labelled data is obtained**
9. **Satellite imagery/context**
10. **Coordinate AI Assistant**
11. **Qwen explanation layer**
12. **Final integration and testing**

Do not block the first working map on ML.
Do not fabricate ML results simply to populate the interface.

## M. Final Demo Flow

1. Open FieryVision AI and immediately show the Giaspura map.
2. Show active/near-real-time FIRMS thermal anomalies.
3. Click a hotspot and show its thermal metrics, contextual evidence, persistence, classification/assessment, and risk.
4. Open satellite context for the event.
5. Open the AI Assistant.
6. Enter latitude and longitude.
7. Show the backend evidence-backed investigation.
8. Ask the assistant why the location is high priority and show an evidence-grounded explanation.

## N. Final Product Message

> **NASA FIRMS tells us WHERE the thermal anomaly is. FieryVision AI adds context, history and intelligence to understand WHAT is likely happening and WHICH events deserve attention.**

**Core product flow:**

```
DETECT -> UNDERSTAND -> ANALYSE -> CLASSIFY -> MONITOR -> PRIORITIZE -> ACT
```