from django.shortcuts import render
from .api.spacedev_api import spacedev_hero, get_upcoming_launches, get_recent_launches, get_completed_launches

# views.py
def show_launches(request):

   # In total, we have 4 API calls for this whole funtion

    hero = spacedev_hero()

    upcoming_list = get_upcoming_launches(limit=4)
    upcoming = upcoming_list[1] if upcoming_list else None

    recent_launches = get_recent_launches(limit=10)
    completed_launches = get_completed_launches(limit=10)

    context = {
        "hero": hero,
        "upcoming": upcoming,               # single launch dict
        "recent": recent_launches,
        "completed": completed_launches,
    }
    return render(request, "launch.html", context)


