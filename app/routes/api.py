"""API routes for the Signal Map service."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..main import get_db
from ..models.database import Location, Fingerprint, Scan, Agent
from ..services.matcher import record_scan, match_location, create_fingerprint
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

router = APIRouter()


# --- Request/Response models ---

class ScanRequest(BaseModel):
    agent_id: str = "android"
    radio: str = "wifi"
    fingerprint: list = []
    label: Optional[str] = None
    gps: Optional[dict] = None


class LocationCreate(BaseModel):
    label: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    fingerprints: Optional[List[dict]] = None


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
def scan(request: ScanRequest, db: Session = Depends(get_db)):
    """Process a signal scan. Returns matched location and coordinates."""
    result = record_scan(db, request.model_dump())
    return result


@router.get("/locations")
def list_locations(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    """List all known locations."""
    locations = db.query(Location).offset(skip).limit(limit).all()
    return [LocationResponse.model_validate(loc) for loc in locations]


@router.get("/locations/{label}")
def get_location(label: str, db: Session = Depends(get_db)):
    """Get a specific location by label."""
    loc = db.query(Location).filter(Location.label == label).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationResponse.model_validate(loc)


@router.post("/locations")
def create_location(request: LocationCreate, db: Session = Depends(get_db)):
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
def list_agents(db: Session = Depends(get_db)):
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
def stats(db: Session = Depends(get_db)):
    """Get map statistics."""
    return {
        "known_locations": db.query(Location).count(),
        "total_scans": db.query(Scan).count(),
        "total_agents": db.query(Agent).count(),
        "total_fingerprints": db.query(Fingerprint).count(),
    }


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "signal-map-api"}
