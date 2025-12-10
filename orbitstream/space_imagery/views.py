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

    print(f"[MEDIA] Processing {media_type} with NASA ID: {nasa_id}")

    # Fetch the asset manifest to get the actual media URL
    asset_url = item.get("href")
    if asset_url:
        try:
            import requests
            print(f"[MEDIA] Fetching assets from: {asset_url}")
            asset_response = requests.get(asset_url)
            if asset_response.status_code == 200:
                assets = asset_response.json()
                print(f"[MEDIA] Found {len(assets)} assets")

                # For images, get the largest available
                if media_type == "image":
                    for url in assets:
                        if "~large" in url:
                            media_url = url
                            break
                    if not media_url:
                        # Fallback to any jpg/png
                        media_url = next((url for url in assets if url.endswith(('.jpg', '.png'))), None)
                    print(f"[MEDIA] Selected image URL: {media_url}")

                # For videos, get the mp4 file
                elif media_type == "video":
                    # Log all available assets to debug
                    print(f"[MEDIA] Available video assets:")
                    for asset in assets:
                        print(f"  - {asset}")

                    media_url = next((url for url in assets if url.endswith('.mp4')), None)
                    print(f"[MEDIA] Selected video URL: {media_url}")
            else:
                print(f"[MEDIA ERROR] Failed to fetch assets: HTTP {asset_response.status_code}")
        except Exception as e:
            print(f"[MEDIA ERROR] Error fetching assets: {e}")
            import traceback
            traceback.print_exc()

    # Fallback to links if available
    if not media_url and item.get("links"):
        media_url = item["links"][0].get("href")
        print(f"[MEDIA] Using fallback link URL: {media_url}")

    if not media_url:
        print(f"[MEDIA WARNING] No media URL found for {nasa_id}")

    # Include the full item with links for thumbnail extraction
    context = {
        "item": item_data,
        "item_links": item.get("links", []),
        "media_url": media_url,
        "media_type": media_type,
        "nasa_id": nasa_id,
    }

    return render(request, "full_media.html", context)