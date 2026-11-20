# Signal Map API

FastAPI-based location mapping service. WiFi/BLE/cell/GPS fingerprint matching
for agents and IoT devices.

## Quick start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API documentation.

## Docker

```bash
docker build -t signal-map-api .
docker run -p 8000:8000 signal-map-api
```

## Tests

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/scan | Process a signal scan |
| GET | /api/locations | List known locations |
| GET | /api/locations/{label} | Get location by label |
| POST | /api/locations | Create a location |
| GET | /api/agents | List registered agents |
| GET | /api/stats | Map statistics |
| GET | /api/health | Health check |

## Example: scan

```bash
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test-agent",
    "radio": "wifi",
    "fingerprint": [
      {"bssid": "aa:bb:cc:00:00:01", "signal": -55},
      {"bssid": "aa:bb:cc:00:00:02", "signal": -61}
    ],
    "gps": {"lat": 34.0, "lon": -118.0, "accuracy": 10, "age_s": 5}
  }'
```
