# FieryVision AI — ML & Evidence Intelligence

## Overview
This layer processes NASA FIRMS satellite observations around the Giaspura, Ludhiana monitoring area into actionable operational intelligence using unsupervised anomaly detection, transparent evidence synthesis, and priority scoring.

## Architecture & Principles

1. **FIRMS as Thermal Anomaly Source**: Raw satellite observations (from NOAA-20 and NOAA-21 VIIRS sensors) identify radiometric surface heat emissions across the study region.
2. **Spatial-Temporal Clustering**: Raw observations within 375 meters and 24 hours are connected into event clusters to avoid treating repeated passes of the same fire episode as disconnected events.
3. **Thermal & Temporal Feature Engineering**: Features are computed per event cluster, including peak and mean Fire Radiative Power (FRP), brightness temperature, spectral difference (`brightness - bright_t31`), multi-day recurrence, and historical spatial neighborhood counts (7d, 30d, 90d).
4. **Unsupervised Isolation Forest**: Detects statistically unusual thermal behaviour within the local empirical distribution using purely numerical thermal and temporal features (excluding raw coordinates to prevent spatial bias). It does **not** predict fire type.
5. **Transparent Evidence Rules**: The evidence engine synthesizes only what the available data honestly supports (thermal intensity, persistence, observation frequency, and detection confidence).
6. **Temporal Persistence Engine**: Categorizes thermal events into `Transient` (1 day), `Recurring` (2–4 days), or `Persistent` (>=5 days).
7. **Priority Scoring**: Computes a transparent 0–100 operational triage score (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`) to prioritize monitoring attention. This is **not** a probability of disaster.
8. **Source Attribution Limitations**: Cause attribution requiring industrial infrastructure or land-cover context is intentionally limited until those layers are injected via the optional context hooks (`industrial_context`, `landcover_context`). Proximity alone never proves causation.
9. **Future Supervised Modeling**: When genuine, ground-verified source labels become available, a supervised classifier can be introduced without disrupting the unsupervised anomaly and evidence pipeline.
