from django.shortcuts import render
from .api.spacedev_api import (
    spacedev_hero,
    get_upcoming_launches,
    get_recent_launches,
    get_completed_launches,
    get_launch_by_id,
)


def show_launches(request):
    hero = spacedev_hero()

    upcoming_list = get_upcoming_launches(limit=5)  # slider uses this
    upcoming = upcoming_list[0] if upcoming_list else None  # keep your single card base if needed

    recent_launches = get_recent_launches(limit=10)
    completed_launches = get_completed_launches(limit=10)

    context = {
        "hero": hero,
        "upcoming": upcoming,
        "upcoming_list": upcoming_list,
        "recent": recent_launches,
        "completed": completed_launches,
    }
    return render(request, "launch.html", context)


def full_launch_detail(request, launch_id):
    """
    Display the full launch detail page for a specific launch ID.
    Includes pad latitude/longitude for the Leaflet map.
    """
    # Get the specific launch data by ID (fallback to empty dict if None)
    launch = get_launch_by_id(launch_id) or {}

    # Safely pull pad + coordinates
    pad = launch.get("pad") or {}
    latitude = pad.get("latitude")
    longitude = pad.get("longitude")

    context = {
        "launch": launch,
        "pad_lat": latitude,
        "pad_lon": longitude,
    }
    return render(request, "full_launch.html", context)
