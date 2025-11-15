# launches/api/spacedev_api.py
import datetime
import os
import time

import requests

SPACEDEVS_BASE = "https://ll.thespacedevs.com/2.0.0"

# --- API key (from env) ---
SPACEDEVS_API_KEY = os.environ.get("SPACEDEV_API_KEY")

# --- Simple in-memory cache ---
CACHE_TTL_SECONDS = 1800  # 30 minutes
_cache = {}  # {key: (timestamp, data)}


def _get_cached(key):
    entry = _cache.get(key)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        return None
    return data


def _set_cache(key, data):
    _cache[key] = (time.time(), data)


def _do_spacedevs_get(path, params=None):
    """
    Helper to call SpaceDevs with the API key and shared params.
    path: like "/launch/upcoming/" or "/launch/previous/"
    params: dict of query params
    """
    if params is None:
        params = {}

    headers = {}
    # Apply Patreon token
    if SPACEDEVS_API_KEY:
        headers["Authorization"] = f"Token {SPACEDEVS_API_KEY}"

    url = f"{SPACEDEVS_BASE}{path}"
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()



def get_next_launch():
    """
    Fetch the next *truly upcoming* launch by:
      1. Asking Launch Library 2 for several upcoming launches.
      2. Filtering in Python to pick the earliest launch whose NET is >= now.
    Uses in-memory caching so we don't hammer the API.
    """
    cache_key = "next_launch"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    params = {
        "limit": 10,                   # grab a few so we can filter
        "ordering": "net",             # earliest first
        "hide_recent_previous": "true"
    }

    try:
        data = _do_spacedevs_get("/launch/upcoming/", params=params)
    except requests.RequestException as e:
        print("SpaceDevs API error:", e)
        # If we had a stale cached value, we already would’ve returned it.
        return None

    results = data.get("results") or []
    if not results:
        return None

    now = datetime.datetime.now(datetime.timezone.utc)

    def parse_net(net_str: str) -> datetime.datetime | None:
        if not net_str:
            return None
        if net_str.endswith("Z"):
            net_str = net_str.replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(net_str)
        except ValueError:
            return None

    future_launches = []
    for launch in results:
        net_str = launch.get("net")
        net_dt = parse_net(net_str)
        if net_dt is None:
            continue
        if net_dt >= now:
            future_launches.append((net_dt, launch))

    if future_launches:
        future_launches.sort(key=lambda pair: pair[0])
        chosen = future_launches[0][1]
    else:
        chosen = results[0]

    _set_cache(cache_key, chosen)
    return chosen


def spacedev_hero():
    """
    Build the hero dictionary used by your template from the next launch.
    Keys:
      - mission_name
      - launch_time
      - background_image
      - rocket_name
      - pad_name
      - pad_location
      - webcast_url (best-effort)
    """
    launch = get_next_launch()
    if not launch:
        return None

    mission_name = launch.get("name")
    launch_time = launch.get("net")
    background_image = launch.get("image")

    rocket = launch.get("rocket") or {}
    rocket_cfg = rocket.get("configuration") or {}
    rocket_name = rocket_cfg.get("full_name")

    pad = launch.get("pad") or {}
    pad_name = pad.get("name")
    location = pad.get("location") or {}
    pad_location = location.get("name")

    webcast_url = launch.get("webcast_live") or launch.get("url")

    return {
        "mission_name": mission_name,
        "launch_time": launch_time,
        "background_image": background_image,
        "rocket_name": rocket_name,
        "pad_name": pad_name,
        "pad_location": pad_location,
        "webcast_url": webcast_url,
    }


# Function to fill the upcoming launches
def get_upcoming_launches(limit=4):
    """
    Return a list of upcoming launches (dicts from Launch Library 2).
    Used for the 'Upcoming Launches' feature card area.
    """
    cache_key = f"upcoming_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    params = {
        "limit": limit,
        "ordering": "net",
        "hide_recent_previous": "true",
    }

    try:
        data = _do_spacedevs_get("/launch/upcoming/", params=params)
    except requests.RequestException as e:
        print("SpaceDevs upcoming error:", e)
        return cached or []

    results = data.get("results") or []

    now = datetime.datetime.now(datetime.timezone.utc)

    def parse_net(net_str):
        if not net_str:
            return None
        if net_str.endswith("Z"):
            net_str = net_str.replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(net_str)
        except ValueError:
            return None

    future = []
    for launch in results:
        net_dt = parse_net(launch.get("net"))
        if net_dt and net_dt >= now:
            future.append(launch)

    _set_cache(cache_key, future)
    return future


# Function to fill recent launches
def get_recent_launches(limit=5):
    """
    Recent launches (most recent first) for the 'Recent Launches' table.
    """
    cache_key = f"recent_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    params = {
        "limit": limit,
        "ordering": "-net",
    }

    try:
        data = _do_spacedevs_get("/launch/previous/", params=params)
    except requests.RequestException as e:
        print("SpaceDevs recent error:", e)
        return cached or []

    results = data.get("results") or []
    _set_cache(cache_key, results)
    return results


# Function for getting completed missions
def get_completed_launches(limit=5):
    """
    Completed launches (i.e., anything in the past).
    """
    cache_key = f"completed_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    params = {
        "limit": limit,
        "ordering": "-net",
    }

    try:
        data = _do_spacedevs_get("/launch/previous/", params=params)
    except requests.RequestException as e:
        print("SpaceDevs Previous API error:", e)
        return cached or []

    results = data.get("results") or []
    _set_cache(cache_key, results)
    return results
