# launches/api/spacedev_api.py
import datetime
import os
import time
import re
import requests
from django.core.cache import cache

SPACEDEVS_BASE = "https://ll.thespacedevs.com/2.2.0"

# --- API key (from env) ---
SPACEDEVS_API_KEY = os.environ.get("SPACEDEV_API_KEY")

# --- Simple in-memory cache ---
CACHE_TTL_SECONDS = 1800  # 30 minutes
_cache = {}  # {key: (timestamp, data)}


def _get_cached(key):
    return cache.get(key)

def _set_cache(key, data):
    cache.set(key, data, CACHE_TTL_SECONDS)


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


def _parse_net_to_dt(net_str):
    if not net_str:
        return None
    if net_str.endswith("Z"):
        net_str = net_str.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(net_str)
    except ValueError:
        return None

def _get_future_upcoming(total_needed: int = 10):
    """
    Internal helper:
    - Calls /launch/upcoming/ ONCE
    - Filters to future launches (net >= now, with parsed net_dt)
    - Returns a list of launches sorted by net
    """
    cache_key = f"future_upcoming_{total_needed}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    params = {
        "limit": total_needed * 2,   # over-fetch a bit in case some are in the past
        "ordering": "net",
        "hide_recent_previous": "true",
    }

    try:
        data = _do_spacedevs_get("/launch/upcoming/", params=params)
    except requests.RequestException as e:
        print("SpaceDevs upcoming error:", e)
        return []

    results = data.get("results") or []
    now = datetime.datetime.now(datetime.timezone.utc)

    future = []
    for launch in results:
        dt = _parse_net_to_dt(launch.get("net"))
        if dt and dt >= now:
            launch["net_dt"] = dt
            future.append(launch)
            if len(future) >= total_needed:
                break

    _set_cache(cache_key, future)
    return future


def extract_youtube_id(url):
    """
    Extract YouTube video ID from various YouTube URL formats.
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID
    """
    if not url:
        return None

    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/live\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def get_best_video_url(launch):
    """
    Return the best video URL for a launch, preferably the 'Official Webcast'
    from launch['vidURLs'], otherwise the first URL available.
    """
    if not launch:
        return None

    vid_urls = launch.get("vidURLs") or []
    if not vid_urls:
        return None

    official = None
    fallback = None

    for entry in vid_urls:
        url = entry.get("url")
        if not url:
            continue

        if not fallback:
            fallback = url

        type_obj = entry.get("type") or {}
        if type_obj.get("name") == "Official Webcast":
            official = url
            break

    return official or fallback

def get_mission_patches(launch):
    """
    Find mission patches.
    FIXED: 
    1. Uses 'name__contains' (double underscore) so the API actually filters.
    2. Uses 'limit': 100 to ensure we see all candidates.
    """
    if not launch:
        return []

    mission = launch.get("mission") or {}
    raw_name = mission.get("name")
    
    if not raw_name:
        return []

    # mission agency ids (for filtering)
    mission_agencies = mission.get("agencies") or []
    mission_agency_ids = {
        a.get("id") for a in mission_agencies if isinstance(a, dict)
    }

    # Cache key
    safe_key = re.sub(r"\s+", "_", raw_name)
    cache_key = f"mission_patches_{safe_key}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # 1) strip anything in parentheses
    base_name = re.sub(r"\s*\(.*?\)", "", raw_name).strip()
    if not base_name:
        base_name = raw_name.strip()
    
    base_name = base_name.replace("-", " ")

    # 2) split into words
    words = base_name.split()
    if not words:
        _set_cache(cache_key, [])
        return []

    def pick_best_patch(results, mission_name):
        mission_lower = mission_name.lower().replace("-", " ")
        mission_tokens = set(re.findall(r"\w+", mission_lower))

        # Filter by agency if possible
        if mission_agency_ids:
            agency_filtered = []
            for p in results:
                agency = p.get("agency") or {}
                if agency.get("id") in mission_agency_ids:
                    agency_filtered.append(p)
            if agency_filtered:
                results = agency_filtered

        # Starlink special case
        if "starlink" in mission_lower:
            starlink_candidates = [
                p for p in results
                if "starlink" in (p.get("name") or "").lower()
            ]
            if starlink_candidates:
                results = starlink_candidates

        # Scoring
        best = None
        best_score = -1
        
        for p in results:
            pname = (p.get("name") or "").lower().replace("-", " ")
            p_tokens = set(re.findall(r"\w+", pname))
            overlap = len(mission_tokens & p_tokens)
            
            if overlap > best_score:
                best_score = overlap
                best = p
            elif overlap == best_score:
                if best and len(pname) < len((best.get("name") or "").lower()):
                    best = p
                     
        return best

    patches = []

    # 3) progressively shorten
    for i in range(len(words)):
        search_term = " ".join(words[:len(words) - i])
        if not search_term:
            break

        params = {
            # --- THE FIX IS HERE ---
            "name__contains": search_term,  # Double Underscore!
            "limit": 100 
        }

        try:
            data = _do_spacedevs_get("/mission_patch/", params=params)
        except requests.RequestException as e:
            print(f"[mission_patches] error for '{search_term}': {e}")
            continue

        results = data.get("results") or []
        
        if not results:
            continue

        best_patch = pick_best_patch(results, raw_name)
        
        if best_patch:
            patches = [best_patch]
            break 

    _set_cache(cache_key, patches)
    return patches



def get_next_launch():
    """
    Next upcoming launch (earliest net >= now).
    """
    future = _get_future_upcoming(total_needed=10)
    return future[0] if future else None



def spacedev_hero():
    """
    Build the hero dictionary used by your template from the next launch.
    """
    launch = get_next_launch()
    if not launch:
        return None

    mission_name = launch.get("name")
    launch_time = launch.get("net")
    background_image = launch.get("image")
    launch_id = launch.get("id")

    rocket = launch.get("rocket") or {}
    rocket_cfg = rocket.get("configuration") or {}
    rocket_name = rocket_cfg.get("full_name")

    pad = launch.get("pad") or {}
    pad_name = pad.get("name")
    location = pad.get("location") or {}
    pad_location = location.get("name")

    video_url = get_best_video_url(launch)
    youtube_id = extract_youtube_id(video_url)

    return {
        "mission_name": mission_name,
        "launch_time": launch_time,
        "background_image": background_image,
        "launch_id": launch_id,
        "rocket_name": rocket_name,
        "pad_name": pad_name,
        "pad_location": pad_location,
        "webcast_url": video_url,   # direct link
        "youtube_id": youtube_id,   # for embed if you want
    }


def get_full_launch_data():
    """
    Get the complete launch object for the detail page.
    Returns the full API response for the next upcoming launch.
    """
    launch = get_next_launch()
    if launch:
        video_url = get_best_video_url(launch)
        youtube_id = extract_youtube_id(video_url)
        launch["video_url"] = video_url
        launch["youtube_id"] = youtube_id
    return launch



def get_launch_by_id(launch_id):
    """
    Fetch a specific launch by its ID.
    Also fetches mission patches if available.
    """
    cache_key = f"launch_{launch_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = _do_spacedevs_get(f"/launch/{launch_id}/")
    except requests.RequestException as e:
        print(f"SpaceDevs API error fetching launch {launch_id}:", e)
        return None

    video_url = get_best_video_url(data)
    youtube_id = extract_youtube_id(video_url)

    data["video_url"] = video_url
    data["youtube_id"] = youtube_id

    # ✅ get the best patch for THIS launch
    mission_patches = get_mission_patches(data)
    data["mission_patches"] = mission_patches

    _set_cache(cache_key, data)
    return data


def get_upcoming_launches(limit):
    """
    Return a list of upcoming launches (dicts from Launch Library 2).
    Used for the 'Upcoming Launches' feature card area.

    We share the same /launch/upcoming/ data as get_next_launch, and
    skip the very next launch (which is used in the hero).
    """
    # we need "hero + limit" items
    total_needed = limit + 1
    cache_key = f"upcoming_{total_needed}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    future = _get_future_upcoming(total_needed=total_needed)
    if not future:
        return []

    # skip the first item (hero)
    upcoming_only = future[1:total_needed] if len(future) > 1 else []

    _set_cache(cache_key, upcoming_only)
    return upcoming_only



def get_recent_and_completed(recent_limit, completed_limit):
    """
    Make ONE call to /launch/previous/ and split it into:
      - recent: newest `recent_limit` launches (any status)
      - completed: older launches where status.name == "Success",
                   up to `completed_limit` items.
    """
    cache_key = f"recent_completed_{recent_limit}_{completed_limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # Grab enough results to cover both lists.
    # We over-fetch a bit so we can filter for completed successes.
    total_limit = recent_limit + completed_limit * 2

    params = {
    "limit": total_limit,
    "ordering": "-net",
    "net__lte": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}


    try:
        data = _do_spacedevs_get("/launch/", params=params)

    except requests.RequestException as e:
        print("SpaceDevs recent+completed error:", e)
        return cached or {"recent": [], "completed": []}

    results = data.get("results") or []

    # Attach parsed datetime for nicer formatting
    for launch in results:
        launch["net_dt"] = _parse_net_to_dt(launch.get("net"))

    # Newest launches → "recent"
    recent = results[:recent_limit]

    # Older launches → candidates for "completed"
    older = results[recent_limit:]
    completed_success = []

    for launch in older:
        status = launch.get("status") or {}
        status_name = status.get("name")
        if status_name in ("Launch Successful", "Success"):
            completed_success.append(launch)
            if len(completed_success) >= completed_limit:
                break

    split_data = {
        "recent": recent,
        "completed": completed_success,
    }

    _set_cache(cache_key, split_data)
    return split_data


def get_recent_launches(limit):
    """
    Recent launches (most recent first) for the 'Recent Launches' table.
    Uses the shared recent+completed helper so we only hit the API once.
    """
    split = get_recent_and_completed(recent_limit=limit, completed_limit=limit)
    return split.get("recent", [])


def get_completed_launches(limit):
    """
    Completed launches for the 'Completed Missions' table.
    Uses the same shared data as get_recent_launches.
    """
    split = get_recent_and_completed(recent_limit=limit, completed_limit=limit)
    return split.get("completed", [])
    