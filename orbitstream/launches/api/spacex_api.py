# launches/api/spacex_api.py
import requests

SPACEX_BASE = "https://api.spacexdata.com/v4"

def get_next_launch():
    try:
        resp = requests.get(f"{SPACEX_BASE}/launches/next")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("SpaceX API Error:", e)
        return None

def get_rocket(rocket_id):
    try:
        resp = requests.get(f"{SPACEX_BASE}/rockets/{rocket_id}")
        resp.raise_for_status()
        return resp.json()
    except:
        return None

def get_launchpad(launchpad_id):
    try:
        resp = requests.get(f"{SPACEX_BASE}/launchpads/{launchpad_id}")
        resp.raise_for_status()
        return resp.json()
    except:
        return None

def spacex_hero():
    launch = get_next_launch()
    if not launch:
        return None
    
    # Mission name
    mission_name = launch.get("name")

    # Launch time
    launch_time = launch.get("date_utc")

    # Links block (for images, webcast, etc.)
    links = launch.get("links", {}) or {}

    # Webcast
    webcast_url = links.get("webcast")

    # Background image:
    # 1) Try flickr.original
    # 2) Then flickr.small
    # 3) Then mission patch (large)
    flickr = links.get("flickr", {}) or {}
    original_images = flickr.get("original") or []
    small_images = flickr.get("small") or []

    background_image = None

    if original_images:
        background_image = original_images[0]
    elif small_images:
        background_image = small_images[0]
    else:
        # fall back to mission patch (not ideal for full-bleed,
        # but better than nothing)
        background_image = links.get("patch", {}).get("large")

    return {
        "mission_name": mission_name,
        "launch_time": launch_time,
        "background_image": background_image,
        "webcast_url": webcast_url,
    }

