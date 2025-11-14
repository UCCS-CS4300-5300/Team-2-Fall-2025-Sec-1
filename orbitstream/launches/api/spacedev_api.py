# launches/api/spacedev_api.py
import requests

SPACEDEVS_BASE = "https://ll.thespacedevs.com/2.0.0"


def get_next_launch():
    """
    Fetch the next upcoming launch from Launch Library 2 (The Space Devs).
    We request 1 result, ordered by NET (no-earlier-than time).
    """
    url = f"{SPACEDEVS_BASE}/launch/upcoming/"
    params = {
        "limit": 1,
        "ordering": "net",  # earliest upcoming launch
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print("SpaceDevs API error:", e)
        return None

    data = resp.json()
    results = data.get("results") or []
    if not results:
        return None

    return results[0]


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

    # Basic fields
    mission_name = launch.get("name")
    launch_time = launch.get("net")  # ISO datetime string
    background_image = launch.get("image")  # hero-style image URL

    # Rocket info
    rocket = launch.get("rocket") or {}
    rocket_cfg = rocket.get("configuration") or {}
    rocket_name = rocket_cfg.get("full_name")

    # Pad / location info
    pad = launch.get("pad") or {}
    pad_name = pad.get("name")
    location = pad.get("location") or {}
    pad_location = location.get("name")

    # Webcast / info URL (best-effort)
    # Some launches have webcast URLs; others just have a detail URL.
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
