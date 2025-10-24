# space_news/views.py
from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from django.utils.text import slugify

from newsapi import NewsApiClient
from news_filter.forms import NewsFilterForm
from news_filter.filters import NewsFilterService
from .utils import fetch_full_html

import requests
from bs4 import BeautifulSoup
from readability import Document
import bleach

import hashlib

def _make_uid(article: dict) -> str:
    """
    Build a stable, slug-safe UID for routing:
    <slug-of-title>-<8-char-hash>
    """
    title = (article.get("title") or "untitled").strip()
    base = slugify(title)[:60] or "article"
    # hash on URL or (title+publishedAt) as fallback for uniqueness
    unique_src = (article.get("url") or (title + (article.get("publishedAt") or ""))).encode("utf-8", "ignore")
    short_hash = hashlib.sha1(unique_src).hexdigest()[:8]
    return f"{base}-{short_hash}"

def _clean_image_url(url):
    """
    Validate and clean image URLs. Return None if invalid.
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Check if it's a valid URL
    if not url.startswith(('http://', 'https://')):
        return None
    
    # Check if it ends with an image extension
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    lower_url = url.lower()
    
    # Some URLs have query params, so check before the '?'
    url_without_query = lower_url.split('?')[0]
    
    if not any(url_without_query.endswith(ext) for ext in valid_extensions):
        # If no extension, still accept if URL contains common image hosting patterns
        image_patterns = ['/image/', '/img/', '/photo/', '/picture/', '/media/']
        if not any(pattern in lower_url for pattern in image_patterns):
            return None
    
    return url

def _remove_duplicates(articles):
    """
    Remove duplicate articles based on title similarity and URL.
    """
    seen_urls = set()
    seen_titles = set()
    unique_articles = []
    
    for article in articles:
        url = article.get('url', '').strip().lower()
        title = article.get('title', '').strip().lower()
        
        # Skip if we've seen this exact URL
        if url and url in seen_urls:
            continue
        
        # Skip if we've seen this exact title
        if title and title in seen_titles:
            continue
        
        # Skip if title is too similar to existing titles (first 50 chars)
        title_prefix = title[:50]
        is_duplicate = False
        for seen_title in seen_titles:
            if title_prefix and seen_title.startswith(title_prefix[:50]):
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        # Add to unique list
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)
        
        unique_articles.append(article)
    
    return unique_articles

def nasa_news(request):
    """
    View to fetch and display NASA and SpaceX space news articles with filtering.
    Populates cache so article_detail can render by uid.
    """
    # Initialize filter form with GET parameters
    filter_form = NewsFilterForm(request.GET or None)

    # Get filter parameters
    filter_params = {}
    if filter_form.is_valid():
        filter_params = {k: v for k, v in filter_form.cleaned_data.items() if v}

    apod = None  # Optional: fetch APOD later if you want
    error = None
    total_results = 0

    try:
        # Initialize News API client
        newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)

        # Base parameters for News API
        base_params = {
            'q': '(NASA OR SpaceX OR "space exploration" OR "space mission") AND (rocket OR satellite OR astronaut OR spacecraft OR launch)',
            'qintitle': 'space OR NASA OR SpaceX',
            'language': 'en',
            'sort_by': 'publishedAt',
            'page_size': 30,  # Fetch more to account for filtering
            'exclude_domains': 'adult-sites.com,inappropriate-domain.com',
        }

        # Apply filter parameters to API call
        api_params = NewsFilterService.build_api_params(filter_params, base_params)

        # Fetch articles with updated parameters
        articles_data = newsapi.get_everything(**api_params)

        if articles_data.get('status') == 'ok':
            raw_articles = articles_data.get('articles', [])
            filtered_articles = []
            inappropriate_keywords = [
                'adult', 'porn', 'xxx', 'celebrity gossip',
                'dating', 'sexy', 'erotic'
            ]

            for article in raw_articles:
                # Lowercased fields for checks
                title_l = (article.get('title') or '').lower()
                description_l = (article.get('description') or '').lower()
                content_l = (article.get('content') or '').lower()

                # Skip if contains inappropriate keywords
                if any(k in title_l or k in description_l or k in content_l for k in inappropriate_keywords):
                    continue

                # Only include if it's genuinely about space/NASA/SpaceX
                if any(term in title_l or term in description_l
                       for term in ['nasa', 'spacex', 'space', 'rocket', 'satellite',
                                    'astronaut', 'spacecraft', 'launch', 'mars', 'moon']):
                    # Add UID for routing
                    article = dict(article)  # shallow copy to avoid mutating original
                    article['uid'] = _make_uid(article)
                    
                    # ✅ FIX #1: Clean and validate image URLs
                    image_url = article.get('urlToImage')
                    cleaned_url = _clean_image_url(image_url)
                    article['urlToImage'] = cleaned_url  # Will be None if invalid
                    
                    filtered_articles.append(article)

            # ✅ FIX #2: Remove duplicates before further filtering
            filtered_articles = _remove_duplicates(filtered_articles)

            # Apply user's custom filters (query, date range, etc.)
            if filter_params:
                filtered_articles = NewsFilterService.apply_filters(filtered_articles, filter_params)

            # Limit to top 20 after all filtering
            filtered_articles = filtered_articles[:20]
            total_results = len(filtered_articles)

            # Cache a lookup for detail pages (10 min)
            articles_by_uid = {str(a['uid']): a for a in filtered_articles if a.get('uid')}
            cache.set("space_news_articles_by_uid", articles_by_uid, timeout=600)

            context = {
                'articles': filtered_articles,
                'total_results': total_results,
                'error': None,
                'filter_form': filter_form,
                'has_active_filters': bool(filter_params),
                'apod': apod,
            }
        else:
            context = {
                'articles': [],
                'total_results': 0,
                'error': 'Failed to fetch articles',
                'filter_form': filter_form,
                'has_active_filters': bool(filter_params),
                'apod': apod,
            }

    except Exception as e:
        context = {
            'articles': [],
            'total_results': 0,
            'error': f'An error occurred: {str(e)}',
            'filter_form': filter_form,
            'has_active_filters': bool(filter_params),
            'apod': apod,
        }

    return render(request, 'space_news/nasa_news.html', context)

def article_detail(request, uid: str):
    # Step 1: pull from cache (your existing behavior)
    articles_by_uid = cache.get("space_news_articles_by_uid") or {}
    article = articles_by_uid.get(str(uid))

    if not article:
        raise Http404("Article not found or expired.")

    # Step 2: if we don't have full text, fetch it from the URL
    full_html = article.get("full_html")
    if not full_html and article.get("url"):
        UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

        def _clean_html(html: str):
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "iframe", "noscript"]):
                tag.decompose()
            for img in soup.find_all("img"):
                img.attrs["loading"] = "lazy"
            cleaned = bleach.clean(
                str(soup),
                tags=["p","h2","h3","h4","ul","ol","li","strong","em","blockquote",
                      "figure","figcaption","img","a","code","pre","br"],
                attributes={
                    "a": ["href","title","rel","target"],
                    "img": ["src","alt","title","width","height","loading"]
                },
                protocols=["http","https","data"],
                strip=True
            )
            # ensure there is text after cleaning
            if BeautifulSoup(cleaned, "lxml").get_text(strip=True):
                return cleaned
            return None

        try:
            # Try normal page
            r = requests.get(article["url"], headers={"User-Agent": UA}, timeout=8)
            r.raise_for_status()
            html = Document(r.text).summary(html_partial=True)
            cleaned = _clean_html(html)

            # AMP fallback if cleaned is empty
            if not cleaned:
                soup0 = BeautifulSoup(r.text, "lxml")
                amp = soup0.find("link", rel=lambda v: v and "amphtml" in v.lower())
                if amp and amp.get("href"):
                    r2 = requests.get(amp["href"], headers={"User-Agent": UA}, timeout=8)
                    r2.raise_for_status()
                    cleaned = _clean_html(r2.text)

            if cleaned:
                # Store back into cache so we don't fetch again
                article["full_html"] = cleaned
                articles_by_uid[str(uid)] = article
                cache.set("space_news_articles_by_uid", articles_by_uid, timeout=60 * 60)
                full_html = cleaned
        except Exception:
            full_html = None

    return render(request, "space_news/article.html", {"article": article, "full_html": full_html})