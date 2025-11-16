# launches/api/spacedev_api.py
import datetime
import os
import time
import re
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


def _parse_net_to_dt(net_str):
    if not net_str:
        return None
    if net_str.endswith("Z"):
        net_str = net_str.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(net_str)
    except ValueError:
        return None


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


def get_mission_patches(mission_id):
    """
    Fetch mission patches for a specific mission ID.
    Returns a list of mission patch objects with image_url.
    """
    cache_key = f"mission_patches_{mission_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    params = {
        "mission": mission_id,
    }

    try:
        data = _do_spacedevs_get("/mission_patches/", params=params)
    except requests.RequestException as e:
        print(f"SpaceDevs API error fetching mission patches for {mission_id}:", e)
        return []

    results = data.get("results") or []
    _set_cache(cache_key, results)
    return results


def get_next_launch():
    """
    Fetch the next *truly upcoming* launch by:
      1. Asking Launch Library 2 for several upcoming launches.
      2. Filtering in Python to pick the earliest launch whose NET is >= now.
    Uses in-memory caching so we don't hammer the API.
    Returns the full launch object with all details.
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
    Now also fetches mission patches if available.
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

    # Fetch mission patches if mission exists
    mission = data.get("mission")
    if mission and mission.get("id"):
        mission_patches = get_mission_patches(mission["id"])
        data["mission_patches"] = mission_patches
    else:
        data["mission_patches"] = []

    _set_cache(cache_key, data)
    return data


def get_upcoming_launches(limit):
    """
    Return a list of upcoming launches (dicts from Launch Library 2).
    Used for the 'Upcoming Launches' feature card area.
    Only returns launches that haven't happened yet.
    """
    cache_key = f"upcoming_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # Request more than needed since we'll filter out past launches
    params = {
        "limit": limit * 3,  # Request 3x to account for filtering
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

    # Filter to only truly future launches
    future = []
    for launch in results:
        net_dt = parse_net(launch.get("net"))
        if net_dt and net_dt >= now:
            launch["net_dt"] = net_dt
            future.append(launch)
            if len(future) >= limit:
                break

    _set_cache(cache_key, future)
    return future


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
    }

    try:
        data = _do_spacedevs_get("/launch/previous/", params=params)
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
        if status_name == "Success":
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
    