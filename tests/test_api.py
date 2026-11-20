"""Tests for the Signal Map API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.models.database import Base
from app.main import engine
from app.models.database import Location, Fingerprint, Agent, Scan

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///./test_signal_map.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app, headers={"X-API-Key": "dev-key-change-in-production"})


class TestHealth:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestLocations:
    def test_create_location(self):
        resp = client.post("/api/locations", json={
            "label": "test-place",
            "lat": 34.0,
            "lon": -118.0,
            "fingerprints": [
                {"radio": "wifi", "entries": [{"bssid": "aa:bb:cc:00:00:01", "signal": -55}]}
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "test-place"
        assert data["lat"] == 34.0

    def test_list_locations(self):
        client.post("/api/locations", json={"label": "place-1", "lat": 34.0, "lon": -118.0})
        client.post("/api/locations", json={"label": "place-2", "lat": 34.1, "lon": -118.1})
        resp = client.get("/api/locations")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_location(self):
        client.post("/api/locations", json={"label": "my-place", "lat": 34.0, "lon": -118.0})
        resp = client.get("/api/locations/my-place")
        assert resp.status_code == 200
        assert resp.json()["label"] == "my-place"

    def test_get_location_not_found(self):
        resp = client.get("/api/locations/nonexistent")
        assert resp.status_code == 404

    def test_duplicate_location(self):
        client.post("/api/locations", json={"label": "dup", "lat": 34.0, "lon": -118.0})
        resp = client.post("/api/locations", json={"label": "dup", "lat": 34.0, "lon": -118.0})
        assert resp.status_code == 409


class TestScan:
    def test_scan_with_gps(self):
        resp = client.post("/api/scan", json={
            "agent_id": "test-agent",
            "radio": "wifi",
            "fingerprint": [{"bssid": "aa:bb:cc:00:00:01", "signal": -55}],
            "gps": {"lat": 34.0, "lon": -118.0, "accuracy": 10, "age_s": 5}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "recorded"
        assert data["method"] == "gps"
        assert data["lat"] == 34.0

    def test_scan_matches_location(self):
        # Create a location
        client.post("/api/locations", json={
            "label": "home",
            "lat": 34.0,
            "lon": -118.0,
            "fingerprints": [
                {"radio": "wifi", "entries": [{"bssid": "aa:bb:cc:00:00:01", "signal": -55}]}
            ]
        })
        # Scan with matching fingerprint
        resp = client.post("/api/scan", json={
            "agent_id": "test-agent",
            "radio": "wifi",
            "fingerprint": [{"bssid": "aa:bb:cc:00:00:01", "signal": -55}]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["location"] == "home"
        assert data["confidence"] > 0.9

    def test_scan_unknown_location(self):
        resp = client.post("/api/scan", json={
            "agent_id": "test-agent",
            "radio": "wifi",
            "fingerprint": [{"bssid": "zz:zz:zz:zz:zz:zz", "signal": -80}]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["location"] == "unknown"

    def test_scan_labels_location(self):
        resp = client.post("/api/scan", json={
            "agent_id": "test-agent",
            "radio": "wifi",
            "fingerprint": [{"bssid": "aa:bb:cc:00:00:01", "signal": -55}],
            "label": "new-place",
            "gps": {"lat": 34.5, "lon": -118.5, "accuracy": 10, "age_s": 5}
        })
        assert resp.status_code == 200
        assert resp.json()["label_stored"] is True
        # Verify location was created
        resp2 = client.get("/api/locations/new-place")
        assert resp2.status_code == 200


class TestStats:
    def test_stats(self):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "known_locations" in data
        assert "total_scans" in data
        assert "total_agents" in data
