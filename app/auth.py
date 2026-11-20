"""API key authentication for the Signal Map API.

Agents authenticate by sending an X-API-Key header.
Keys are stored in environment variables or a config file.

For development, set API_KEY=dev-key in environment.
For production, use a secrets manager or environment variable.
"""
import os
from fastapi import Security, HTTPException, Depends
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Default key for development. Override with API_KEY env var.
DEFAULT_API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify the API key from the request header."""
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if api_key != DEFAULT_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# Optional auth dependency - can be used on specific routes
# For now, auth is optional (auto_error=False) to allow testing
# In production, set API_KEY env var and require it on all routes
def optional_auth(api_key: str = Security(API_KEY_HEADER)):
    """Optional auth - returns the key if valid, None if not provided."""
    if api_key is None:
        return None
    if api_key != DEFAULT_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
