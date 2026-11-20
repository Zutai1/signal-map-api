"""Python client for the Signal Map API.

Usage:
    from signal_map_client import SignalMapClient

    client = SignalMapClient(base_url="http://localhost:8000", api_key="dev-key")
    
    # Scan
    result = client.scan(
        agent_id="my-agent",
        radio="wifi",
        fingerprint=[{"bssid": "aa:bb:cc:00:00:01", "signal": -55}],
        gps={"lat": 34.0, "lon": -118.0, "accuracy": 10, "age_s": 5}
    )
    print(result["location"], result["confidence"])
    
    # Get location
    loc = client.get_location("home")
    print(loc["lat"], loc["lon"])
    
    # List all locations
    locations = client.list_locations()
    print(len(locations))
    
    # Get stats
    stats = client.stats()
    print(stats["known_locations"])
"""
import requests
from typing import Optional, List, Dict, Any


class SignalMapClient:
    """Client for the Signal Map API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["X-API-Key"] = api_key

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict:
        """Check if the service is healthy."""
        return self._request("GET", "/api/health")

    def scan(
        self,
        agent_id: str = "agent",
        radio: str = "wifi",
        fingerprint: List[dict] = None,
        label: Optional[str] = None,
        gps: Optional[dict] = None,
    ) -> dict:
        """Send a signal scan. Returns matched location and coordinates."""
        data = {
            "agent_id": agent_id,
            "radio": radio,
            "fingerprint": fingerprint or [],
        }
        if label:
            data["label"] = label
        if gps:
            data["gps"] = gps
        return self._request("POST", "/api/scan", json=data)

    def list_locations(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """List all known locations."""
        return self._request("GET", "/api/locations", params={"skip": skip, "limit": limit})

    def get_location(self, label: str) -> dict:
        """Get a specific location by label."""
        return self._request("GET", f"/api/locations/{label}")

    def create_location(
        self,
        label: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        fingerprints: Optional[List[dict]] = None,
    ) -> dict:
        """Create a new location."""
        data = {"label": label}
        if lat is not None:
            data["lat"] = lat
        if lon is not None:
            data["lon"] = lon
        if fingerprints:
            data["fingerprints"] = fingerprints
        return self._request("POST", "/api/locations", json=data)

    def list_agents(self) -> List[dict]:
        """List all registered agents."""
        return self._request("GET", "/api/agents")

    def stats(self) -> dict:
        """Get map statistics."""
        return self._request("GET", "/api/stats")

    def scan_multi(
        self,
        agent_id: str = "agent",
        wifi: Optional[List[dict]] = None,
        ble: Optional[List[dict]] = None,
        cell: Optional[List[dict]] = None,
        gps: Optional[dict] = None,
        label: Optional[str] = None,
    ) -> dict:
        """Send WiFi, BLE, and cell as separate scans. Returns best match."""
        results = {}
        best = None
        best_conf = 0.0

        if wifi:
            r = self.scan(agent_id=f"{agent_id}-wifi", radio="wifi",
                         fingerprint=wifi, label=label, gps=gps)
            results["wifi"] = r
            if r.get("confidence", 0) > best_conf:
                best_conf = r["confidence"]
                best = ("wifi", r)

        if ble:
            ble_fp = [{"bssid": f"ble:{b['mac']}", "signal": b.get("signal", -70)} for b in ble]
            r = self.scan(agent_id=f"{agent_id}-ble", radio="ble",
                         fingerprint=ble_fp, gps=gps)
            results["ble"] = r
            if r.get("confidence", 0) > best_conf:
                best_conf = r["confidence"]
                best = ("ble", r)

        if cell:
            cell_fp = [{"bssid": f"cell:{c.get('type', '?')}:{c.get('cell_id', '?')}",
                        "signal": c.get("signal", -95)} for c in cell]
            r = self.scan(agent_id=f"{agent_id}-cell", radio="cell",
                         fingerprint=cell_fp, gps=gps)
            results["cell"] = r
            if r.get("confidence", 0) > best_conf:
                best_conf = r["confidence"]
                best = ("cell", r)

        if best:
            results["best_radio"] = best[0]
            results["best_result"] = best[1]

        return results


# Convenience function for agents
def locate(base_url: str = "http://localhost:8000", api_key: Optional[str] = None,
           agent_id: str = "agent", **kwargs) -> dict:
    """One-shot location lookup. Returns best match."""
    client = SignalMapClient(base_url=base_url, api_key=api_key)
    return client.scan_multi(agent_id=agent_id, **kwargs)
