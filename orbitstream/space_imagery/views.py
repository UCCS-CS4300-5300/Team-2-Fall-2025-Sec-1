from django.shortcuts import render
from . import utils

def gallery(request):
    q = request.GET.get("q", "")
    media_type = request.GET.get("type", "image")
    page = request.GET.get("page", "1")

    # Only search if there's a query
    if q:
        data = utils.get("search", {"q": q, "media_type": media_type, "page": page})
        items = data.get("collection", {}).get("items", [])
    else:
        items = []

    return render(request, "gallery.html", {
        "items": items,
        "media_type": media_type,
        "q": q,
        "page": page,
    })
