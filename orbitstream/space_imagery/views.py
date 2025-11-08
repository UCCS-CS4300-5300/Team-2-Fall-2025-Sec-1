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

def full_media(request):
    """Display full media (image or video) with details"""
    nasa_id = request.GET.get("nasa_id")
    
    if not nasa_id:
        return render(request, "full_media.html", {"error": "No media ID provided"})
    
    # Get media details
    data = utils.get("search", {"nasa_id": nasa_id})
    items = data.get("collection", {}).get("items", [])
    
    if not items:
        return render(request, "full_media.html", {"error": "Media not found"})
    
    item = items[0]
    item_data = item.get("data", [{}])[0]
    
    # Get the actual media URL (image or video)
    media_url = None
    media_type = item_data.get("media_type", "image")
    
    # Fetch the asset manifest to get the actual media URL
    asset_url = item.get("href")
    if asset_url:
        try:
            import requests
            asset_response = requests.get(asset_url)
            if asset_response.status_code == 200:
                assets = asset_response.json()
                
                # For images, get the largest available
                if media_type == "image":
                    for url in assets:
                        if "~large" in url:
                            media_url = url
                            break
                    if not media_url:
                        # Fallback to any jpg/png
                        media_url = next((url for url in assets if url.endswith(('.jpg', '.png'))), None)
                
                # For videos, get the mp4 file
                elif media_type == "video":
                    media_url = next((url for url in assets if url.endswith('.mp4')), None)
        except:
            pass
    
    # Fallback to links if available
    if not media_url and item.get("links"):
        media_url = item["links"][0].get("href")
    
    context = {
        "item": item_data,
        "media_url": media_url,
        "media_type": media_type,
        "nasa_id": nasa_id,
    }
    
    return render(request, "full_media.html", context)