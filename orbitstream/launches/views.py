from django.shortcuts import render
from .api.spacedev_api import spacedev_hero

def show_launches(request):

    hero = spacedev_hero()

    context = {
       "hero": hero
    }
    
    return render(request, "launch.html", context)

