"""API routes for the Signal Map service."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..main import get_db
from ..models.database import Location, Fingerprint, Scan, Agent
from ..services.matcher import record_scan
from ..auth import verify_api_key
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timezone

router = APIRouter()


# --- Request/Response models with validation ---

class ScanRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=100)
    radio: str = Field(default="wifi", pattern="^(wifi|ble|cell)$")
    fingerprint: list = Field(default=[])
    label: Optional[str] = Field(default=None, max_length=100)
    gps: Optional[dict] = None

    @field_validator("fingerprint")
    @classmethod
    def validate_fingerprint(cls, v):
        if not isinstance(v, list):
            raise ValueError("fingerprint must be a list")
        if len(v) > 50:
            raise ValueError("fingerprint cannot exceed 50 entries")
        for entry in v:
            if not isinstance(entry, dict):
                raise ValueError("each fingerprint entry must be a dict")
            if "bssid" not in entry:
                raise ValueError("each entry must have a bssid")
            if "signal" in entry and not isinstance(entry["signal"], (int, float)):
                raise ValueError("signal must be a number")
        return v

    @field_validator("gps")
    @classmethod
    def validate_gps(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("gps must be a dict")
        if "lat" in v and not isinstance(v["lat"], (int, float)):
            raise ValueError("lat must be a number")
        if "lon" in v and not isinstance(v["lon"], (int, float)):
            raise ValueError("lon must be a number")
        if "lat" in v and ("lon" not in v):
            raise ValueError("lon required if lat provided")
        return v

    @field_validator("label")
    @classmethod
    def validate_label(cls, v):
        if v is None:
            return v
        # Prevent path traversal and injection
        import re
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v):
            raise ValueError("label must contain only alphanumeric, underscore, hyphen, or dot characters")
        return v


class LocationCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    fingerprints: Optional[List[dict]] = None

    @field_validator("label")
    @classmethod
    def validate_label(cls, v):
        import re
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v):
            raise ValueError("label must contain only alphanumeric, underscore, hyphen, or dot characters")
        return v


class LocationResponse(BaseModel):
    id: int
    label: str
    lat: Optional[float]
    lon: Optional[float]
    scan_count: int
    has_wifi: bool
    has_ble: bool
    has_cell: bool
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post("/scan")
def scan(request: ScanRequest, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Process a signal scan. Returns matched location and coordinates."""
    from ..services.matcher import record_scan
    result = record_scan(db, request.model_dump())
    return result


@router.get("/locations")
def list_locations(db: Session = Depends(get_db), skip: int = 0, limit: int = 100, api_key: str = Depends(verify_api_key)):
    """List all known locations."""
    if skip < 0 or limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")
    locations = db.query(Location).offset(skip).limit(limit).all()
    return [LocationResponse.model_validate(loc) for loc in locations]


@router.get("/locations/{label}")
def get_location(label: str, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Get a specific location by label."""
    loc = db.query(Location).filter(Location.label == label).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationResponse.model_validate(loc)


@router.post("/locations")
def create_location(request: LocationCreate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Create a new location with optional fingerprints."""
    existing = db.query(Location).filter(Location.label == request.label).first()
    if existing:
        raise HTTPException(status_code=409, detail="Location already exists")
    loc = Location(label=request.label, lat=request.lat, lon=request.lon)
    db.add(loc)
    db.flush()
    if request.fingerprints:
        for fp in request.fingerprints:
            radio = fp.get("radio", "wifi")
            entries = fp.get("entries", fp.get("fingerprint", []))
            db.add(Fingerprint(location_id=loc.id, radio=radio, entries=entries))
            if radio == "wifi":
                loc.has_wifi = True
            elif radio == "ble":
                loc.has_ble = True
            elif radio == "cell":
                loc.has_cell = True
    db.commit()
    db.refresh(loc)
    return LocationResponse.model_validate(loc)


@router.get("/agents")
def list_agents(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """List all registered agents."""
    agents = db.query(Agent).all()
    return [
        {
            "agent_id": a.agent_id,
            "location": a.location.label if a.location else "unknown",
            "confidence": a.confidence,
            "lat": a.lat,
            "lon": a.lon,
            "method": a.method,
            "radio": a.radio,
            "last_seen": a.last_seen,
        }
        for a in agents
    ]


@router.get("/stats")
def stats(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Get map statistics."""
    return {
        "known_locations": db.query(Location).count(),
        "total_scans": db.query(Scan).count(),
        "total_agents": db.query(Agent).count(),
        "total_fingerprints": db.query(Fingerprint).count(),
    }


@router.get("/health")
def health():
    """Health check endpoint (no auth required)."""
    return {"status": "ok", "service": "signal-map-api"}
