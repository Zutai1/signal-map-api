"""Database models for the Signal Map API.

Uses SQLAlchemy 2.0 with SQLite (dev) / PostgreSQL (prod).
Tables:
  - locations: known places with fingerprints and coordinates
  - fingerprints: individual radio fingerprints per location
  - scans: incoming scan records
  - agents: registered devices/agents
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(255), unique=True, nullable=False, index=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    scan_count = Column(Integer, default=0)
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    has_wifi = Column(Boolean, default=False)
    has_ble = Column(Boolean, default=False)
    has_cell = Column(Boolean, default=False)

    fingerprints = relationship("Fingerprint", back_populates="location", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="location")


class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    radio = Column(String(10), nullable=False)  # wifi, ble, cell
    entries = Column(JSON, nullable=False)  # list of {bssid, signal}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    location = relationship("Location", back_populates="fingerprints")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(100), nullable=False, index=True)
    radio = Column(String(10), nullable=False)
    matched_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    confidence = Column(Float, default=0.0)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    method = Column(String(50), nullable=True)
    fingerprint_hash = Column(String(32), nullable=True)
    raw_fingerprint = Column(JSON, nullable=True)
    gps = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    location = relationship("Location", back_populates="scans")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(100), unique=True, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    confidence = Column(Float, default=0.0)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    method = Column(String(50), nullable=True)
    radio = Column(String(10), nullable=True)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fingerprint_hash = Column(String(32), nullable=True)

    location = relationship("Location")
