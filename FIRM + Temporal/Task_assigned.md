You are responsible ONLY for the FIRMS data pipeline and temporal/persistence analysis of FieryVision AI.

MODEL:
- Gemini 3.8 Flash
- Medium effort
- Keep token usage low.
- Implement directly; do NOT create a plan or write a long explanation.
- Inspect only files relevant to this task.
- Do not modify frontend/.
- Do not modify backend/ except if a tiny shared schema import is strictly necessary; prefer creating reusable modules under data_processing/.
- Do not modify ml/ unless absolutely necessary.
- Do not redesign the repository.
- Do not build unrelated features.
- Do not fabricate data.
- Stop when the acceptance criteria are satisfied.

TARGET:
Giaspura, Ludhiana, Punjab
Center:
latitude = 30.875625
longitude = 75.898481

The approved project uses a regional internal data buffer around Giaspura, while the product remains Giaspura-focused.

==================================================
TASK 1 — FIRMS HISTORICAL DATA
==================================================

Inspect the repository for any existing FIRMS CSV/data files.

If actual FIRMS data exists:
- inspect its schema
- preserve raw files
- create a reusable loader
- validate latitude/longitude/date/time/FRP/confidence
- normalize fields to a consistent schema

If no FIRMS data exists locally:
- create the loader and ingestion implementation so it can consume a NASA FIRMS CSV without changing its schema assumptions unnecessarily
- do not fabricate sample observations

Normalized event fields should support:

event_id
latitude
longitude
acq_date
acq_time
frp
brightness
confidence
satellite
daynight

Also preserve source-specific fields where useful.

==================================================
TASK 2 — NASA FIRMS ACTIVE DATA SERVICE
==================================================

Implement a reusable Python service under:

data_processing/firms/

It must support active/near-real-time FIRMS retrieval using FIRMS_MAP_KEY from environment variables.

Use VIIRS NOAA-20 / NOAA-21 NRT products according to the approved architecture.

Requirements:
- never expose the API key
- use httpx/requests or an already installed HTTP client
- normalize the response
- return clean Python records/DataFrame
- include fetch timestamp/source information
- fail gracefully when API access is unavailable
- never fabricate current observations

If API access is unavailable during development, do not block the rest of the module; keep the service implementation valid and test it using a small locally defined fixture only for unit tests.

Do not make frontend requests directly to NASA.

==================================================
TASK 3 — GEOGRAPHIC FILTERING
==================================================

Implement a reusable function to filter FIRMS observations to the FieryVision Giaspura regional monitoring area.

Use:
latitude = 30.875625
longitude = 75.898481

Use a configurable regional radius, default 50 km.

Use metric distance calculations correctly.

Do not hard-code coordinates throughout multiple files.

Create one configuration/constant source.

==================================================
TASK 4 — EVENT CLUSTERING
==================================================

Implement spatial-temporal clustering for nearby FIRMS detections.

Initial prototype parameters:
- spatial scale: approximately 375 m
- temporal window: approximately 24 hours

Use DBSCAN or an equivalent robust method.

Parameters must be configurable.

The purpose is to reduce duplicate/multiple satellite detections representing the same real-world thermal event.

Do not claim that clustering proves events are identical.

==================================================
TASK 5 — TEMPORAL FEATURES
==================================================

For every event cluster, calculate:

detections_7d
detections_30d
unique_detection_days
average_frp
maximum_frp
first_seen
last_seen

Use historical FIRMS observations.

Return clean structured output.

==================================================
TASK 6 — PERSISTENCE CLASSIFICATION
==================================================

Implement the approved prototype persistence categories:

Transient:
1 unique detection day in the 30-day analysis window

Recurring:
2–4 unique detection days

Persistent:
>= 5 unique detection days

These are prototype thresholds and must be configurable.

Do not present them as universal scientific definitions.

Return:

persistence = "Transient" | "Recurring" | "Persistent" | "Unknown"

==================================================
TASK 7 — OUTPUT
==================================================

Create reusable modules under:

data_processing/firms/
data_processing/temporal/

Produce processed outputs under:

data/processed/

Do not commit large raw external datasets unless they are already intentionally tracked by the repository.

Prefer generated processing outputs to be reproducible from source data.

==================================================
TASK 8 — TESTS
==================================================

Create targeted tests for:

1. FIRMS schema normalization
2. coordinate validation
3. Giaspura 50 km filtering
4. clustering
5. 7-day/30-day aggregation
6. unique detection day calculation
7. persistence classification
8. graceful empty-data handling

Use small fixtures for tests.

==================================================
DO NOT
==================================================

- Do not build ML classification.
- Do not build risk scoring.
- Do not build React.
- Do not build FastAPI routes.
- Do not create fake FIRMS events.
- Do not create fake labels.
- Do not install unnecessary packages.
- Do not refactor unrelated modules.

==================================================
ACCEPTANCE CRITERIA
==================================================

Complete implementation only when:

1. FIRMS historical loader works.
2. FIRMS active retrieval service exists and handles missing API access safely.
3. Giaspura regional filtering works.
4. Spatial-temporal clustering works.
5. Temporal features are generated.
6. Persistence classification works.
7. Reusable modules are importable.
8. Targeted tests pass.
9. No fake data is introduced.
10. Only relevant files were changed.

After validation, report only:
- files created/modified
- packages added
- tests run
- any real blocker

Then STOP.