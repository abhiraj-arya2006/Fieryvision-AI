# 🔥 FieryVision AI

**AI-Powered Industrial Fire Risk Detection & Satellite Intelligence Monitoring Platform**  
*Target Study Area: Giaspura, Ludhiana, Punjab, India (30.875625°N, 75.898481°E · 15 km Regional Buffer)*

---

## 📌 Project Overview

**FieryVision AI** is an industrial thermal anomaly detection and wildfire intelligence platform. It fuses near-real-time satellite thermal imaging (NASA FIRMS / VIIRS / MODIS) with high-resolution landcover data (ESA WorldCover), regional geospatial facility directories, temporal persistence analysis, and unsupervised Machine Learning (Isolation Forest) to detect and prioritize industrial heat anomalies and fire threats.

### Key Capabilities
- **Geospatial Command Center:** Interactive Leaflet map displaying active thermal events, regional industrial facility clusters, and a 15 km regional buffer around Giaspura.
- **Evidence-Based Risk Scoring:** Multi-factor evidence engine calculating risk scores (0–100) and priority tiers (`CRITICAL`, `HIGH`, `MODERATE`, `LOW`).
- **ML Anomaly Detection:** Server-side Isolation Forest pipeline flagging abnormal thermal signatures and intense thermal outliers against baseline operations.
- **Arbitrary Coordinate AI Investigation:** On-demand analysis of any lat/lon coordinate with automatic proximity queries, landcover classification, and historical persistence lookups.
- **Local LLM Intelligence:** Grounded question answering via local Ollama (`qwen2.5:14b`) based strictly on real geospatial investigation context.
- **Satellite Context Telemetry:** Multi-band sensor telemetry, spatial resolution, and satellite metadata inspection per thermal detection.

---

## 🏛️ Architecture Diagram

```
                              ┌──────────────────────────────────────────────┐
                              │           Client Browser                     │
                              │       http://localhost:5173                  │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
                              ┌──────────────────────────────────────────────┐
                              │       React + TypeScript + Vite Frontend     │
                              │   - Leaflet & React-Leaflet MapView          │
                              │   - Recharts Visual Analytics                │
                              │   - Centralized Typed API Service Layer      │
                              │   - Tailwind CSS Command Center Theme        │
                              └──────────────────────┬───────────────────────┘
                                                     │ HTTP / REST
                                                     ▼
                              ┌──────────────────────────────────────────────┐
                              │          FastAPI Backend (Python)            │
                              │       http://localhost:8000                  │
                              │   - Router: /api/health, /api/active-events, │
                              │     /api/events/{id}, /api/facilities,       │
                              │     /api/statistics, /api/analyse-location,  │
                              │     /api/satellite-context, /api/chat        │
                              └─────────┬─────────────┬─────────────┬────────┘
                                        │             │             │
                    ┌───────────────────┘             │             └───────────────────┐
                    ▼                                 ▼                                 ▼
   ┌────────────────────────────────┐ ┌────────────────────────────────┐ ┌────────────────────────────────┐
   │        Python ML Services      │ │      Data Processing & Geo     │ │      Database & External APIs  │
   │ - Isolation Forest Pipeline    │ │ - Haversine Proximity Engine   │ │ - SQLite (fieryvision.db)      │
   │ - Evidence Engine Scoring      │ │ - ESA WorldCover Raster        │ │ - NASA FIRMS Active / Cache    │
   │ - Priority Risk Calculation    │ │ - Temporal Persistence (7d/30d)│ │ - Local Ollama (Qwen2.5:14b)   │
   └────────────────────────────────┘ └────────────────────────────────┘ └────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Leaflet, React-Leaflet, Lucide React, Recharts |
| **Backend** | FastAPI, Python 3.12, Uvicorn, Pydantic v2, SQLAlchemy, HTTPX |
| **Machine Learning** | Scikit-Learn (Isolation Forest), Joblib, NumPy, Pandas |
| **Geospatial & Data** | Rasterio, Shapely, PyProj, NASA FIRMS API, ESA WorldCover raster |
| **Database** | SQLite (`fieryvision.db`) |
| **AI / LLM** | Ollama with `qwen2.5:14b` (optional, offline fallback supported) |

---

## 📂 Folder Structure

```
fieryvision-AI/
├── frontend/                     # Modern React + TypeScript + Vite application
│   ├── src/
│   │   ├── components/           # MapView, Navbar, EventDetailsDrawer, FilterBar, etc.
│   │   ├── hooks/                # useActiveEvents, useFacilities, useStatistics, etc.
│   │   ├── pages/                # MapDashboardPage, AssistantPage, FacilitiesPage, StatisticsPage
│   │   ├── services/             # Centralized typed API service layer (api.ts)
│   │   ├── types/                # TypeScript interfaces mapped to FastAPI schemas
│   │   ├── utils/                # Formatters, color mappings, coordinate math
│   │   ├── App.tsx               # Root component with React Router
│   │   ├── main.tsx              # Entry point
│   │   └── index.css             # Design tokens, Leaflet dark styles, Tailwind
│   ├── public/                   # Static assets (logo, icons)
│   ├── package.json
│   ├── vite.config.ts            # Vite config with port 5173 & /api proxy to :8000
│   └── .env.example
│
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── api/router.py         # All REST endpoints (/api/*)
│   │   ├── core/                 # Config, Database engine, Geospatial math
│   │   ├── models/database.py    # SQLAlchemy database models
│   │   ├── schemas/event.py      # Pydantic schemas (contracts)
│   │   └── services/             # FIRMS, Anomaly, Evidence, Industrial, Temporal services
│   ├── tests/                    # Backend API unit tests
│   ├── main.py                   # FastAPI application initialization & CORS
│   ├── requirements.txt          # Python dependencies
│   └── .env.example
│
├── ml/                           # Machine Learning inference & pipelines
│   ├── models/                   # Isolation Forest pipeline & detector class
│   ├── evidence/                 # Multi-factor evidence engine
│   └── risk/                     # Priority scoring engine
│
├── data/                         # Geospatial datasets, industrial clusters, and landcover
├── data_processing/              # Raster processing, FIRMS collectors, spatial indexers
├── scripts/                      # Utility scripts & dev runner (start-dev.js)
├── tests/                        # Geospatial, ML evidence, and feature test suites
├── fieryvision.db                # SQLite database
├── pytest.ini                    # Pytest configuration
├── package.json                  # Root runner package.json
└── README.md                     # Documentation
```

---

## ⚙️ Environment Variables

### Backend Configuration (`backend/.env`)
```env
FIRMS_MAP_KEY=                     # Optional NASA FIRMS API key (uses cached fallback if blank)
BACKEND_URL=http://localhost:8000  # Backend host URL
OLLAMA_BASE_URL=http://localhost:11434 # Local Ollama LLM endpoint (optional)
OLLAMA_MODEL=qwen2.5:14b          # Local LLM model identifier
FRONTEND_URL=http://localhost:5173 # Allowed CORS frontend origin
```

### Frontend Configuration (`frontend/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000 # Backend API base URL
```

---

## 🚀 Running Locally

### Prerequisites
- **Node.js** (v18+ or v20+ recommended)
- **Python** (3.10, 3.11, or 3.12)
- **npm** or **yarn**

---

### Option 1: Run Both Together (Recommended)

1. **Install Frontend Dependencies:**
   ```bash
   npm run install:frontend
   ```

2. **Install Backend Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Start Both Frontend and Backend:**
   ```bash
   npm run dev
   ```
   - **Frontend:** [http://localhost:5173](http://localhost:5173)
   - **Backend:** [http://localhost:8000](http://localhost:8000)
   - **Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Run Separately

#### Running the Backend
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```
*API will be available at [http://localhost:8000](http://localhost:8000)*

#### Running the Frontend
```bash
cd frontend
npm install
npm run dev
```
*Frontend will open at [http://localhost:5173](http://localhost:5173)*

---

## 📡 API Documentation & Endpoints

All backend routes are documented interactively via OpenAPI / Swagger at:  
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check, FIRMS availability, and classification mode |
| `GET` | `/api/active-events` | Active/recent FIRMS thermal anomalies filtered to Giaspura 15km zone |
| `GET` | `/api/events/{event_id}` | Detailed canonical analysis of an event (evidence, ML anomaly, telemetry) |
| `GET` | `/api/facilities` | Industrial sites, stamping mills, and dyeing plants in Giaspura |
| `GET` | `/api/statistics` | Aggregated threat counts, classification metrics, priority breakdown |
| `POST` | `/api/analyse-location` | Coordinate analysis (Lat/Lon) with spatial query, ML score, and evidence |
| `GET` | `/api/satellite-context/{event_id}` | Satellite platform, sensor resolution, and spectral band metadata |
| `POST` | `/api/chat` | Context-grounded Q&A via local Ollama LLM (`qwen2.5:14b`) |

---

## 🧪 Testing

The repository contains 43 unit and integration tests covering geospatial calculations, ML isolation forest anomaly inference, multi-factor evidence scoring, and FastAPI endpoints.

Run the test suite from the repository root:
```bash
python -m pytest
```

Output:
```
======================= 43 passed, 3 warnings in 11.50s =======================
```

To run frontend TypeScript and production build checks:
```bash
cd frontend
npx tsc --noEmit
npm run build
```

---

## 🛡️ Production & Deployment Notes

- **CORS:** Configured in `backend/main.py` allowing `http://localhost:5173` and `http://127.0.0.1:5173`.
- **Offline / Graceful Fallback:** If the NASA FIRMS API key is absent or unreachable, the system automatically uses verified baseline historical data for Giaspura without failing.
- **LLM Decoupling:** If the local Ollama instance is not running, the system returns evidence-backed heuristic summaries without crashing the application.
- **Security:** Secrets and credentials are kept in `.env` files and excluded via `.gitignore`.
