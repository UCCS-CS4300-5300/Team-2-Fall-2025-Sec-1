import json
import requests
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from .models import (
    SavedSatellite,
    SavedGalleryItem,
    SavedLaunch,
    SavedLearnTopic,
    SavedNewsArticle,
)


def download_file_from_url(url, timeout=60):
    """Download a file from a URL and return its content"""
    try:
        print(f"[DOWNLOAD] Starting download from: {url}")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        # Get content length if available
        content_length = response.headers.get('content-length')
        if content_length:
            print(f"[DOWNLOAD] Content length: {int(content_length) / 1024 / 1024:.2f} MB")

        # For large files (like videos), stream the download
        content = BytesIO()
        chunk_size = 8192
        downloaded = 0
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                content.write(chunk)
                downloaded += len(chunk)

        print(f"[DOWNLOAD] Downloaded {downloaded / 1024 / 1024:.2f} MB")
        content.seek(0)
        return content
    except requests.Timeout as e:
        print(f"[DOWNLOAD ERROR] Timeout downloading file from {url}: {e}")
        return None
    except requests.RequestException as e:
        print(f"[DOWNLOAD ERROR] Request error downloading file from {url}: {e}")
        return None
    except Exception as e:
        print(f"[DOWNLOAD ERROR] Unexpected error downloading file from {url}: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_thumbnail(image_file, size=(300, 300)):
    """Create a thumbnail from an image file"""
    try:
        img = Image.open(image_file)
        img.thumbnail(size, Image.Resampling.LANCZOS)

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        thumb_io.seek(0)
        return ContentFile(thumb_io.read())
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


@login_required
def saved_page(request):
    """Main saved page view showing all saved content organized by category"""
    context = {
        'saved_satellites': SavedSatellite.objects.filter(user=request.user),
        'saved_gallery_items': SavedGalleryItem.objects.filter(user=request.user),
        'saved_launches': SavedLaunch.objects.filter(user=request.user),
        'saved_learn_topics': SavedLearnTopic.objects.filter(user=request.user),
        'saved_news_articles': SavedNewsArticle.objects.filter(user=request.user),
    }
    return render(request, 'saved_page/saved_page.html', context)


@login_required
@require_POST
def toggle_save_satellite(request):
    """Toggle save/unsave for a satellite"""
    try:
        data = json.loads(request.body)
        satellite_id = data.get('satellite_id')
        name = data.get('name', '')

        existing = SavedSatellite.objects.filter(
            user=request.user,
            satellite_id=satellite_id
        ).first()

        if existing:
            existing.delete()
            return JsonResponse({'saved': False, 'message': 'Satellite removed from saved'})

        SavedSatellite.objects.create(
            user=request.user,
            satellite_id=satellite_id,
            name=name,
            altitude=data.get('altitude'),
            azimuth=data.get('azimuth'),
            elevation=data.get('elevation'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
        )
        return JsonResponse({'saved': True, 'message': 'Satellite saved'})
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def toggle_save_gallery(request):
    """Toggle save/unsave for a gallery item"""
    try:
        data = json.loads(request.body)
        nasa_id = data.get('nasa_id')
        title = data.get('title', '')

        print(f"[SAVE] Attempting to save gallery item: nasa_id={nasa_id}, type={data.get('media_type')}")

        existing = SavedGalleryItem.objects.filter(
            user=request.user,
            nasa_id=nasa_id
        ).first()

        if existing:
            existing.delete()
            print(f"[SAVE] Removed existing gallery item: {nasa_id}")
            return JsonResponse({'saved': False, 'message': 'Gallery item removed from saved'})

        # Get URLs
        media_url = data.get('media_url')
        thumbnail_url = data.get('thumbnail_url')
        media_type = data.get('media_type', 'image')

        print(f"[SAVE] Media URL: {media_url}")
        print(f"[SAVE] Thumbnail URL: {thumbnail_url}")
        print(f"[SAVE] Media type: {media_type}")

        # Validate required fields
        if not media_url:
            print(f"[SAVE ERROR] No media URL provided for {nasa_id}")
            return JsonResponse({'error': 'Media URL is required'}, status=400)

        # Create the gallery item
        gallery_item = SavedGalleryItem(
            user=request.user,
            nasa_id=nasa_id,
            title=title,
            description=data.get('description'),
            media_url=media_url,
            thumbnail_url=thumbnail_url,
            media_type=media_type,
        )

        # Download and save media data to database
        if media_url:
            try:
                print(f"[SAVE] Downloading media from: {media_url}")
                media_content = download_file_from_url(media_url)
                if media_content:
                    # Generate a safe filename
                    import os
                    extension = os.path.splitext(media_url)[1][:10]
                    if not extension or '?' in extension:
                        extension = '.jpg' if media_type == 'image' else '.mp4'
                    filename = f"{nasa_id}{extension}"

                    # Store binary data in database
                    media_bytes = media_content.read()
                    gallery_item.media_data = media_bytes
                    gallery_item.media_filename = filename
                    print(f"[SAVE] Saved media data: {len(media_bytes)} bytes")

                    # Determine content type
                    if media_type == 'image':
                        gallery_item.media_content_type = 'image/jpeg'
                    elif media_type == 'video':
                        gallery_item.media_content_type = 'video/mp4'
                    else:
                        gallery_item.media_content_type = 'application/octet-stream'

                    # Create thumbnail for images
                    if media_type == 'image':
                        media_content.seek(0)
                        thumbnail_content = create_thumbnail(media_content)
                        if thumbnail_content:
                            thumb_bytes = thumbnail_content.read()
                            gallery_item.thumbnail_data = thumb_bytes
                            gallery_item.thumbnail_filename = f"{nasa_id}_thumb.jpg"
                            gallery_item.thumbnail_content_type = 'image/jpeg'
                            print(f"[SAVE] Created thumbnail: {len(thumb_bytes)} bytes")
                else:
                    print(f"[SAVE ERROR] Failed to download media from {media_url}")
                    return JsonResponse({'error': 'Failed to download media file'}, status=400)
            except Exception as e:
                print(f"[SAVE ERROR] Error saving media data: {e}")
                import traceback
                traceback.print_exc()
                return JsonResponse({'error': f'Error downloading media: {str(e)}'}, status=400)

        # Download and save thumbnail (if not already created from image)
        if thumbnail_url and not gallery_item.thumbnail_data:
            try:
                print(f"[SAVE] Downloading thumbnail from: {thumbnail_url}")
                thumb_content = download_file_from_url(thumbnail_url)
                if thumb_content:
                    thumb_bytes = thumb_content.read()
                    gallery_item.thumbnail_data = thumb_bytes
                    gallery_item.thumbnail_filename = f"{nasa_id}_thumb.jpg"
                    gallery_item.thumbnail_content_type = 'image/jpeg'
                    print(f"[SAVE] Saved thumbnail: {len(thumb_bytes)} bytes")
            except Exception as e:
                print(f"[SAVE WARNING] Error saving thumbnail: {e}")
                # Don't fail the entire save if just thumbnail fails

        gallery_item.save()
        print(f"[SAVE SUCCESS] Saved gallery item: {nasa_id}")
        return JsonResponse({'saved': True, 'message': 'Gallery item saved'})
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[SAVE ERROR] JSON/Key error: {e}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        print(f"[SAVE ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)


@login_required
@require_POST
def toggle_save_launch(request):
    """Toggle save/unsave for a launch"""
    try:
        data = json.loads(request.body)
        launch_id = str(data.get('launch_id'))
        name = data.get('name', '')

        existing = SavedLaunch.objects.filter(
            user=request.user,
            launch_id=launch_id
        ).first()

        if existing:
            existing.delete()
            return JsonResponse({'saved': False, 'message': 'Launch removed from saved'})

        SavedLaunch.objects.create(
            user=request.user,
            launch_id=launch_id,
            name=name,
            status=data.get('status'),
            net=data.get('net'),
            rocket_name=data.get('rocket_name'),
            pad_name=data.get('pad_name'),
            pad_location=data.get('pad_location'),
            image_url=data.get('image_url'),
        )
        return JsonResponse({'saved': True, 'message': 'Launch saved'})
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def toggle_save_learn(request):
    """Toggle save/unsave for a learn topic"""
    try:
        data = json.loads(request.body)
        topic = data.get('topic')
        summary = data.get('summary', '')

        existing = SavedLearnTopic.objects.filter(
            user=request.user,
            topic=topic
        ).first()

        if existing:
            existing.delete()
            return JsonResponse({'saved': False, 'message': 'Topic removed from saved'})

        SavedLearnTopic.objects.create(
            user=request.user,
            topic=topic,
            summary=summary,
            keywords=data.get('keywords'),
        )
        return JsonResponse({'saved': True, 'message': 'Topic saved'})
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def toggle_save_news(request):
    """Toggle save/unsave for a news article"""
    try:
        data = json.loads(request.body)
        article_url = data.get('article_url')
        title = data.get('title', '')

        existing = SavedNewsArticle.objects.filter(
            user=request.user,
            article_url=article_url
        ).first()

        if existing:
            existing.delete()
            return JsonResponse({'saved': False, 'message': 'Article removed from saved'})

        SavedNewsArticle.objects.create(
            user=request.user,
            article_url=article_url,
            title=title,
            description=data.get('description'),
            image_url=data.get('image_url'),
            source_name=data.get('source_name'),
            published_at=data.get('published_at'),
            full_html=data.get('full_html'),
            content=data.get('content'),
            author=data.get('author'),
        )
        return JsonResponse({'saved': True, 'message': 'Article saved'})
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def check_saved_satellite(request):
    """Check if a satellite is saved"""
    satellite_id = request.GET.get('satellite_id')
    if not satellite_id:
        return JsonResponse({'error': 'satellite_id required'}, status=400)

    is_saved = SavedSatellite.objects.filter(
        user=request.user,
        satellite_id=satellite_id
    ).exists()
    return JsonResponse({'saved': is_saved})


@login_required
def check_saved_gallery(request):
    """Check if a gallery item is saved"""
    nasa_id = request.GET.get('nasa_id')
    if not nasa_id:
        return JsonResponse({'error': 'nasa_id required'}, status=400)

    is_saved = SavedGalleryItem.objects.filter(
        user=request.user,
        nasa_id=nasa_id
    ).exists()
    return JsonResponse({'saved': is_saved})


@login_required
def check_saved_launch(request):
    """Check if a launch is saved"""
    launch_id = request.GET.get('launch_id')
    if not launch_id:
        return JsonResponse({'error': 'launch_id required'}, status=400)

    is_saved = SavedLaunch.objects.filter(
        user=request.user,
        launch_id=launch_id
    ).exists()
    return JsonResponse({'saved': is_saved})


@login_required
def check_saved_learn(request):
    """Check if a learn topic is saved"""
    topic = request.GET.get('topic')
    if not topic:
        return JsonResponse({'error': 'topic required'}, status=400)

    is_saved = SavedLearnTopic.objects.filter(
        user=request.user,
        topic=topic
    ).exists()
    return JsonResponse({'saved': is_saved})


@login_required
def check_saved_news(request):
    """Check if a news article is saved"""
    article_url = request.GET.get('article_url')
    if not article_url:
        return JsonResponse({'error': 'article_url required'}, status=400)

    is_saved = SavedNewsArticle.objects.filter(
        user=request.user,
        article_url=article_url
    ).exists()
    return JsonResponse({'saved': is_saved})


@login_required
def get_saved_ids(request):
    """Get all saved IDs for the current user (for batch checking on list pages)"""
    saved_data = {
        'satellites': list(
            SavedSatellite.objects.filter(user=request.user).values_list('satellite_id', flat=True)
        ),
        'gallery': list(
            SavedGalleryItem.objects.filter(user=request.user).values_list('nasa_id', flat=True)
        ),
        'launches': list(
            SavedLaunch.objects.filter(user=request.user).values_list('launch_id', flat=True)
        ),
        'learn': list(
            SavedLearnTopic.objects.filter(user=request.user).values_list('topic', flat=True)
        ),
        'news': list(
            SavedNewsArticle.objects.filter(user=request.user).values_list('article_url', flat=True)
        ),
    }
    return JsonResponse(saved_data)


@login_required
@require_POST
def delete_saved_satellite(request, pk):
    """Delete a saved satellite"""
    try:
        item = SavedSatellite.objects.get(pk=pk, user=request.user)
        item.delete()
        return JsonResponse({'success': True})
    except SavedSatellite.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_POST
def delete_saved_gallery(request, pk):
    """Delete a saved gallery item"""
    try:
        item = SavedGalleryItem.objects.get(pk=pk, user=request.user)
        item.delete()
        return JsonResponse({'success': True})
    except SavedGalleryItem.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_POST
def delete_saved_launch(request, pk):
    """Delete a saved launch"""
    try:
        item = SavedLaunch.objects.get(pk=pk, user=request.user)
        item.delete()
        return JsonResponse({'success': True})
    except SavedLaunch.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_POST
def delete_saved_learn(request, pk):
    """Delete a saved learn topic"""
    try:
        item = SavedLearnTopic.objects.get(pk=pk, user=request.user)
        item.delete()
        return JsonResponse({'success': True})
    except SavedLearnTopic.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
@require_POST
def delete_saved_news(request, pk):
    """Delete a saved news article"""
    try:
        item = SavedNewsArticle.objects.get(pk=pk, user=request.user)
        item.delete()
        return JsonResponse({'success': True})
    except SavedNewsArticle.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
def view_saved_article(request, pk):
    """Display a saved news article in OrbitStream's article format"""
    saved_article = get_object_or_404(SavedNewsArticle, pk=pk, user=request.user)

    # Format the saved article data to match what article.html expects
    article = {
        'title': saved_article.title,
        'description': saved_article.description,
        'url': saved_article.article_url,
        'urlToImage': saved_article.image_url,
        'source': {
            'name': saved_article.source_name or 'Unknown Source'
        },
        'publishedAt': saved_article.published_at,
        'author': saved_article.author,
        'content': saved_article.content,
    }

    context = {
        'article': article,
        'full_html': saved_article.full_html,  # Use the saved full HTML content
        'is_saved_view': True,  # Flag to indicate this is a saved article view
    }

    return render(request, 'space_news/article.html', context)


@login_required
def view_saved_media(request, pk):
    """Display a saved gallery media item"""
    saved_media = get_object_or_404(SavedGalleryItem, pk=pk, user=request.user)

    # Use database-served media if available, otherwise fall back to URL
    from django.urls import reverse
    media_url = reverse('saved_page:serve_gallery_media', args=[pk]) if saved_media.media_data else saved_media.media_url
    thumbnail_url = reverse('saved_page:serve_gallery_thumbnail', args=[pk]) if saved_media.thumbnail_data else saved_media.thumbnail_url

    context = {
        'media_item': saved_media,
        'media_url': media_url,
        'thumbnail_url': thumbnail_url,
        'is_saved_view': True,
    }

    return render(request, 'saved_page/saved_media.html', context)


@login_required
def serve_gallery_media(request, pk):
    """Serve media data from database"""
    from django.http import HttpResponse
    saved_media = get_object_or_404(SavedGalleryItem, pk=pk, user=request.user)

    if not saved_media.media_data:
        raise Http404("Media data not found")

    response = HttpResponse(
        saved_media.media_data,
        content_type=saved_media.media_content_type or 'application/octet-stream'
    )
    if saved_media.media_filename:
        response['Content-Disposition'] = f'inline; filename="{saved_media.media_filename}"'
    return response


@login_required
def serve_gallery_thumbnail(request, pk):
    """Serve thumbnail data from database"""
    from django.http import HttpResponse
    saved_media = get_object_or_404(SavedGalleryItem, pk=pk, user=request.user)

    if not saved_media.thumbnail_data:
        raise Http404("Thumbnail data not found")

    response = HttpResponse(
        saved_media.thumbnail_data,
        content_type=saved_media.thumbnail_content_type or 'image/jpeg'
    )
    if saved_media.thumbnail_filename:
        response['Content-Disposition'] = f'inline; filename="{saved_media.thumbnail_filename}"'
    return response
