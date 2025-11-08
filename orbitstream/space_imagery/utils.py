from typing import Dict, Any, Optional
import requests
from django.conf import settings

BASE = "https://images-api.nasa.gov"
SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json",   
    "User-Agent": "OrbitStream"
})

class NasaApiError(Exception):
    pass


def _add_key(params: Optional[Dict[str, Any]]):
    p = dict(params or {})
    p["api_key"] = settings.NASA_API_KEY
    return p


def get(path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15):
    """Helper to make GET requests to NASA API."""
    url = f"{BASE.rstrip('/')}/{path.lstrip('/')}"
    resp = SESSION.get(url, params=params, timeout=timeout)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = {"error": resp.text}
        raise NasaApiError(f"NASA {resp.status_code}: {detail}")
    return resp.json()
