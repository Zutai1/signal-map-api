# Deploying the Signal Map API

## Local development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker (recommended for production)

```bash
docker build -t signal-map-api .
docker run -d -p 8000:8000 \
  -e API_KEY=your-secret-key \
  -e DATABASE_URL=sqlite:///./data/signal_map.db \
  -v signal-map-data:/app/data \
  signal-map-api
```

## Cloud deployment

### Railway (easiest)
1. Push to GitHub
2. Connect Railway to your repo
3. Set `API_KEY` environment variable
4. Railway auto-deploys on push

### Render
1. Create a new Web Service
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set `API_KEY` environment variable

### AWS EC2 / GCP Compute
1. Launch a small instance (t3.micro / e2-micro)
2. Install Docker
3. Run the Docker command above
4. Open port 8000 in security group

## Agent integration

### Python agent

```python
from signal_map_client import SignalMapClient

client = SignalMapClient(base_url="http://your-server:8000", api_key="your-key")

# One-shot location
result = client.scan_multi(
    agent_id="my-agent",
    wifi=[{"bssid": "aa:bb:cc:00:00:01", "signal": -55}],
    ble=[{"mac": "f0:70:4f:3c:af:7f", "signal": -70}],
    gps={"lat": 34.0, "lon": -118.0, "accuracy": 10, "age_s": 5}
)
print(result["best_result"]["location"])
```

### Shell agent (curl)

```bash
curl -X POST http://your-server:8000/api/scan \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"agent_id": "shell-agent", "radio": "wifi", "fingerprint": [{"bssid": "aa:bb:cc:00:00:01", "signal": -55}]}'
```

### Agent on Raspberry Pi

```bash
# Install
pip install requests
# Copy signal_map_client.py to your project
# Use in your daemon:
python3 -c "
from signal_map_client import SignalMapClient
client = SignalMapClient(base_url='http://your-server:8000', api_key='your-key')
print(client.stats())
"
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `dev-key-change-in-production` | API authentication key |
| `DATABASE_URL` | `sqlite:///./signal_map.db` | Database connection string |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

## Security notes

- Change `API_KEY` in production
- Use PostgreSQL for production (SQLite is for development)
- Put behind a reverse proxy (nginx/caddy) for HTTPS
- Rate limiting is not built in — add via nginx or a middleware
