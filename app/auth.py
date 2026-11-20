"""API key authentication for the Signal Map API.

Agents authenticate by sending an X-API-Key header.
Keys are stored in environment variables.
"""
import os
from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

DEFAULT_API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify the API key from the request header. Required on all routes."""
    if api_key != DEFAULT_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
