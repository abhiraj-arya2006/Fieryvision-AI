# FieryVision AI — Backend Service

FastAPI backend & satellite intelligence integration layer for **Giaspura, Ludhiana, Punjab**.

## Setup & Virtual Environment

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a Virtual Environment**:
   - Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set environment variables in `.env`:
- `FIRMS_MAP_KEY`: NASA FIRMS API key (optional; defaults to cached baseline dataset if omitted)
- `BACKEND_URL`: URL of this FastAPI server (default: `http://localhost:8000`)
- `OLLAMA_BASE_URL`: Local Ollama Qwen service (default: `http://localhost:11434`)
- `FRONTEND_URL`: Frontend web application URL for CORS (default: `http://localhost:5173`)

## Running the Backend Server

Start the development server with Uvicorn:
```bash
uvicorn main:app --reload --port 8000
```
Interactive API docs are available at: `http://localhost:8000/docs`

## Available Endpoints

- `GET /api/health`: Health status, FIRMS status, and classification mode
- `GET /api/active-events`: Active / recent FIRMS thermal events in Giaspura
- `GET /api/events/{event_id}`: Full canonical analysis for a specific event
- `GET /api/facilities`: Cached Giaspura industrial facility sites
- `GET /api/statistics`: Event summary & classification breakdown
- `POST /api/analyse-location`: Coordinate investigation for arbitrary lat/lon
- `GET /api/satellite-context/{event_id}`: Satellite radiometric context metadata

## Example Coordinate Analysis Request

**POST** `/api/analyse-location`
```json
{
  "latitude": 30.875625,
  "longitude": 75.898481
}
```

## Running Tests

Run targeted pytest suite:
```bash
pytest tests/
```
