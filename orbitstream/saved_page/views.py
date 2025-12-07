import json
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

        existing = SavedGalleryItem.objects.filter(
            user=request.user,
            nasa_id=nasa_id
        ).first()

        if existing:
            existing.delete()
            return JsonResponse({'saved': False, 'message': 'Gallery item removed from saved'})

        SavedGalleryItem.objects.create(
            user=request.user,
            nasa_id=nasa_id,
            title=title,
            description=data.get('description'),
            media_url=data.get('media_url'),
            thumbnail_url=data.get('thumbnail_url'),
            media_type=data.get('media_type', 'image'),
        )
        return JsonResponse({'saved': True, 'message': 'Gallery item saved'})
    except (json.JSONDecodeError, KeyError) as e:
        return JsonResponse({'error': str(e)}, status=400)


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
