# space_news/views.py
from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.utils.text import slugify

from newsapi import NewsApiClient
from news_filter.forms import NewsFilterForm
from news_filter.filters import NewsFilterService
from .utils import fetch_full_html  # if you use it elsewhere
from .config import (
    SPACE_KEYWORDS_ALL,
    EXCLUDED_TOPICS_ALL,
    INAPPROPRIATE_KEYWORDS,
    EXCLUDED_DOMAINS,
    RELIABLE_IMAGE_SOURCES,
    NEWS_API_QUERY,
    NEWS_API_TITLE_QUERY,
    MAX_ARTICLES_PER_SOURCE,
    TOTAL_ARTICLES_LIMIT,
)

import requests
from bs4 import BeautifulSoup
from readability import Document
import bleach
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
import random
from datetime import datetime, timedelta
import random


def fetch_apod(date=None):
    """
    Get NASA APOD once an hour and normalize to the keys nasa_news.html expects.

    Args:
        date: Optional date string in 'YYYY-MM-DD' format.
              If None, fetches today's APOD.
              Can also be 'random' to get a random historical APOD.

    Returns a dict like:
      {"title","date","url","media_type","explanation","copyright"}
    or None on failure.
    """
    # Create cache key based on date
    if date == 'random':
        # Don't cache random requests
        cache_key = None
    elif date:
        cache_key = f"apod:{date}"
    else:
        cache_key = "apod:current"

    # Check cache
    if cache_key:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
    api_key = getattr(settings, "NASA_API_KEY", None)
    print(f"DEBUG: NASA_API_KEY = {api_key}")
    if not api_key:
        print("ERROR: NASA_API_KEY is not set!")
        return None

    try:
        params = {"api_key": api_key, "thumbs": True}

        # Handle random date
        if date == 'random':
            # APOD started on June 16, 1995
            start_date = datetime(1995, 6, 16)
            end_date = datetime.now()
            time_between = end_date - start_date
            days_between = time_between.days
            random_days = random.randrange(days_between)
            random_date = start_date + timedelta(days=random_days)
            date = random_date.strftime('%Y-%m-%d')

        # Add date parameter if specified
        if date:
            params['date'] = date

        # Retry logic with longer timeout
        max_retries = 1
        for attempt in range(max_retries):
            try:
                r = requests.get(NASA_APOD_URL, params=params, timeout=20)
                r.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise
                print(f"APOD request timeout, retrying... (attempt {attempt + 1}/{max_retries})")

        data = r.json()

        media_type = data.get("media_type", "image")
        # Template uses a single key: apod.url
        # - For images: prefer HD if available; else url
        # - For video: use the video URL (YouTube/Vimeo/etc.)
        url = data.get("hdurl") or data.get("url")
        if media_type == "video":
            url = data.get("url")  # iframe src

        apod = {
            "title": data.get("title"),
            "date": data.get("date"),
            "url": url,
            "media_type": media_type,
            "explanation": data.get("explanation"),
            "copyright": data.get("copyright"),
        }

        # Cache the result
        if cache_key:
            # Cache historical dates for longer (24 hours)
            # Cache current date for 1 hour
            timeout = 60 * 60 * 24 if date else 60 * 60
            cache.set(cache_key, apod, timeout=timeout)

        return apod
    except Exception as e:
        print(f"APOD fetch error: {e}")
        import traceback
        traceback.print_exc()

        # Fallback: Return a rotating static APOD if API fails
        print("Using fallback APOD data...")

        # Array of fallback APODs
        fallback_apods = [
            {
                "title": "The Pencil Nebula Supernova Shock Wave",
                "date": "2024-02-23",
                "url": "https://apod.nasa.gov/apod/image/2402/NGC2736_Helge_Buesing1024.jpg",
                "media_type": "image",
                "explanation": "This supernova shock wave plows through interstellar space at over 500,000 kilometers per hour",
                "copyright": "Helge Buesing"
            },
            {
                "title": "Enceladus by Saturnshine",
                "date": "2023-02-05",
                "url": "https://apod.nasa.gov/apod/image/2302/enceladus12_cassini_960.jpg",
                "media_type": "image",
                "explanation": "This moon is shining by the light of its planet. Specifically, a large portion of Enceladus pictured here is illuminated primarily by sunlight first reflected from the planet Saturn.",
                "copyright": "Gordan Ugarkovic"
            },
            {
                "title": "A Cosmic Rose: The Rosette Nebula in Monoceros",
                "date": "2019-04-12",
                "url": "https://apod.nasa.gov/apod/image/1904/JMD_Rosette_Rotated1024.jpg",
                "media_type": "image",
                "explanation": "The Rosette Nebula, NGC 2237, is not the only cosmic cloud of gas and dust to evoke the imagery of flowers, but it is the most famous. At the edge of a large molecular cloud in Monoceros some 5,000 light years away, the petals of this cosmic rose are actually a stellar nursery. The lovely, symmetric shape is sculpted by the winds and radiation from its central cluster of hot young, O-type stars.",
                "copyright": "Jean Dean"
            },
            {
                "title": "M101: The Pinwheel Galaxy",
                "date": "2003-03-10",
                "url": "https://apod.nasa.gov/apod/image/0303/m101_cfht.jpg",
                "media_type": "image",
                "explanation": "Why do many galaxies appear as spirals? A striking example is M101, shown above, whose relatively close distance of about 22 million light years allow it to be studied in some detail.",
                "copyright": "Jean-Charles Cuillandre (CFHT), Hawaiian Starlight, CFHT"
            },
            {
                "title": "Elliptical Galaxy M87",
                "date": "2004-07-16",
                "url": "https://apod.nasa.gov/apod/image/0406/m87_cfht.jpg",
                "media_type": "image",
                "explanation": "Elliptical galaxy M87 is a type of galaxy that looks much different than our own Milky Way Galaxy. ",
                "copyright": "Canada-France-Hawaii Telescope, J.-C. Cuillandre (CFHT), Coelum"
            },

        ]

        # Use day of year to rotate through fallbacks (changes daily)
        from datetime import datetime
        day_of_year = datetime.now().timetuple().tm_yday
        fallback_index = day_of_year % len(fallback_apods)
        fallback_apod = fallback_apods[fallback_index]

        print(f"Selected fallback #{fallback_index + 1}: {fallback_apod['title']}")

        # Cache the fallback briefly (5 minutes) so we don't spam retries
        if cache_key:
            cache.set(cache_key, fallback_apod, timeout=300)

        return fallback_apod


def fetch_apod_async(request):
    """
    AJAX endpoint to fetch APOD asynchronously.
    Called by JavaScript after page loads.

    Supports query parameters:
    - date: Specific date in YYYY-MM-DD format
    - random: If present, fetches a random historical APOD
    """
    date_param = request.GET.get('date')
    random_param = request.GET.get('random')

    if random_param:
        apod = fetch_apod('random')
    elif date_param:
        # Validate date format
        try:
            datetime.strptime(date_param, '%Y-%m-%d')
            apod = fetch_apod(date_param)
        except ValueError:
            return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
    else:
        apod = fetch_apod()

    if apod:
        return JsonResponse(apod)
    return JsonResponse({"error": "APOD unavailable"}, status=503)


def _make_uid(article: dict) -> str:
    """
    Build a stable, slug-safe UID for routing:
    <slug-of-title>-<8-char-hash>
    """
    title = (article.get("title") or "untitled").strip()
    base = slugify(title)[:60] or "article"
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

    # Must be http(s)
    if not url.startswith(("http://", "https://")):
        return None

    # Accept common image extensions (allow query strings)
    valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif", ".svg")
    lower_url = url.lower()
    url_without_query = lower_url.split("?")[0]

    if not any(url_without_query.endswith(ext) for ext in valid_extensions):
        # If no extension, still accept if URL contains common image hosting patterns
        image_patterns = ["/image/", "/img/", "/photo/", "/picture/", "/media/"]
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
        url = (article.get("url") or "").strip().lower()
        title = (article.get("title") or "").strip().lower()

        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue

        title_prefix = title[:50]
        is_duplicate = False
        for seen_title in seen_titles:
            if title_prefix and seen_title.startswith(title_prefix[:50]):
                is_duplicate = True
                break
        if is_duplicate:
            continue

        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)

        unique_articles.append(article)

    return unique_articles


def _prioritize_sources(articles):
    """
    Move articles from reliable image sources to the front of the list.
    These sources consistently have high-quality images and authoritative content.
    """
    priority = []
    regular = []

    for article in articles:
        url = (article.get('url') or '').lower()
        source_name = (article.get('source', {}).get('name') or '').lower()

        # Check if article is from a reliable source
        is_reliable = any(
            source in url or source.replace('.', ' ') in source_name
            for source in RELIABLE_IMAGE_SOURCES
        )

        if is_reliable:
            priority.append(article)
        else:
            regular.append(article)

    return priority + regular


def _is_excluded_domain(article_url, excluded_domains):
    """
    Check if article URL contains any excluded domain.
    This catches domains that slip through NewsAPI's exclude_domains.
    """
    if not article_url:
        return False

    url_lower = article_url.lower()
    return any(domain.lower() in url_lower for domain in excluded_domains)


def nasa_news(request):
    """
    Fetch and display NASA/SpaceX news with filtering.
    Optimized with source prioritization and domain blacklisting.
    """
    filter_form = NewsFilterForm(request.GET or None)

    filter_params = {}
    if filter_form.is_valid():
        filter_params = {k: v for k, v in filter_form.cleaned_data.items() if v}

    # Toggle via query string (?images_only=0 to disable). Default ON.
    images_only = request.GET.get("images_only", "1") not in ("0", "false", "False")

    # Check cache only - don't fetch during page load
    apod = cache.get("apod:current")
    apod_error = None

    if not apod or not apod.get("url"):
        apod_error = "Loading Astronomy Picture of the Day..."

    total_results = 0

    try:
        newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)

        base_params = {
            "q": NEWS_API_QUERY,
            "qintitle": NEWS_API_TITLE_QUERY,
            "language": "en",
            "sort_by": "publishedAt",
            "page_size": 60,
            "exclude_domains": ",".join(EXCLUDED_DOMAINS),
        }

        api_params = NewsFilterService.build_api_params(filter_params, base_params)
        articles_data = newsapi.get_everything(**api_params)

        if articles_data.get("status") == "ok":
            raw_articles = articles_data.get("articles", [])
            filtered_articles = []

            for article in raw_articles:
                title_l = (article.get("title") or "").lower()
                description_l = (article.get("description") or "").lower()
                content_l = (article.get("content") or "").lower()
                article_url = article.get("url") or ""

                # Skip excluded domains (manual check in case NewsAPI doesn't filter them)
                if _is_excluded_domain(article_url, EXCLUDED_DOMAINS):
                    continue

                # Skip if contains inappropriate keywords
                if any(k in title_l or k in description_l or k in content_l for k in INAPPROPRIATE_KEYWORDS):
                    continue

                # Stricter space-related filtering - must contain space keywords
                has_space_keyword = any(
                    keyword in title_l or keyword in description_l
                    for keyword in SPACE_KEYWORDS_ALL
                )

                if not has_space_keyword:
                    continue

                # Skip if article is primarily about excluded topics
                has_excluded_topic = any(
                    topic in title_l or topic in description_l
                    for topic in EXCLUDED_TOPICS_ALL
                )

                if has_excluded_topic:
                    continue

                # Only include if it's genuinely about space/NASA/SpaceX missions
                a = dict(article)
                a["uid"] = _make_uid(a)

                # Clean/validate image URL
                image_url = a.get("urlToImage")
                cleaned_url = _clean_image_url(image_url)
                a["urlToImage"] = cleaned_url  # may be None

                # If images_only is True, skip articles without image URLs
                if images_only and not cleaned_url:
                    continue

                filtered_articles.append(a)

            # Deduplicate
            filtered_articles = _remove_duplicates(filtered_articles)

            # Prioritize articles from reliable sources (those with consistently good images)
            filtered_articles = _prioritize_sources(filtered_articles)

            # Apply user filters (query/date/etc.)
            if filter_params:
                filtered_articles = NewsFilterService.apply_filters(filtered_articles, filter_params)

            # Diversity filter: Limit to max articles per source for variety
            source_counts = defaultdict(int)
            diverse_articles = []

            for article in filtered_articles:
                source_name = article.get('source', {}).get('name', '')
                if source_counts[source_name] < MAX_ARTICLES_PER_SOURCE:
                    diverse_articles.append(article)
                    source_counts[source_name] += 1

            filtered_articles = diverse_articles

            # Limit to configured maximum
            filtered_articles = filtered_articles[:TOTAL_ARTICLES_LIMIT]
            total_results = len(filtered_articles)

            # Cache for detail pages (10 min)
            articles_by_uid = {str(a["uid"]): a for a in filtered_articles if a.get("uid")}
            cache.set("space_news_articles_by_uid", articles_by_uid, timeout=600)

            context = {
                "articles": filtered_articles,
                "total_results": total_results,
                "error": None,
                "filter_form": filter_form,
                "has_active_filters": bool(filter_params),
                "apod": apod,
                "apod_error": apod_error,
                "images_only": images_only,
            }
        else:
            context = {
                "articles": [],
                "total_results": 0,
                "error": "Failed to fetch articles",
                "filter_form": filter_form,
                "has_active_filters": bool(filter_params),
                "apod": apod,
                "apod_error": apod_error,
                "images_only": images_only,
            }

    except Exception as e:
        context = {
            "articles": [],
            "total_results": 0,
            "error": f"An error occurred: {str(e)}",
            "filter_form": filter_form,
            "has_active_filters": bool(filter_params),
            "apod": apod,
            "apod_error": apod_error,
            "images_only": images_only,
        }

    return render(request, "space_news/nasa_news.html", context)


def article_detail(request, uid: str):
    """
    Article detail: fetch from cache by uid; if needed, pull and sanitize full HTML from source.
    """
    articles_by_uid = cache.get("space_news_articles_by_uid") or {}
    article = articles_by_uid.get(str(uid))

    if not article:
        raise Http404("Article not found or expired.")

    full_html = article.get("full_html")
    if not full_html and article.get("url"):
        UA = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )

        def _clean_html(html: str):
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "iframe", "noscript"]):
                tag.decompose()
            for img in soup.find_all("img"):
                img.attrs["loading"] = "lazy"
            cleaned = bleach.clean(
                str(soup),
                tags=[
                    "p",
                    "h2",
                    "h3",
                    "h4",
                    "ul",
                    "ol",
                    "li",
                    "strong",
                    "em",
                    "blockquote",
                    "figure",
                    "figcaption",
                    "img",
                    "a",
                    "code",
                    "pre",
                    "br",
                ],
                attributes={
                    "a": ["href", "title", "rel", "target"],
                    "img": ["src", "alt", "title", "width", "height", "loading"],
                },
                protocols=["http", "https", "data"],
                strip=True,
            )
            if BeautifulSoup(cleaned, "lxml").get_text(strip=True):
                return cleaned
            return None

        try:
            r = requests.get(article["url"], headers={"User-Agent": UA}, timeout=8)
            r.raise_for_status()
            html = Document(r.text).summary(html_partial=True)
            cleaned = _clean_html(html)

            # AMP fallback
            if not cleaned:
                soup0 = BeautifulSoup(r.text, "lxml")
                amp = soup0.find("link", rel=lambda v: v and "amphtml" in v.lower())
                if amp and amp.get("href"):
                    r2 = requests.get(amp["href"], headers={"User-Agent": UA}, timeout=8)
                    r2.raise_for_status()
                    cleaned = _clean_html(r2.text)

            if cleaned:
                article["full_html"] = cleaned
                articles_by_uid[str(uid)] = article
                cache.set("space_news_articles_by_uid", articles_by_uid, timeout=60 * 60)
                full_html = cleaned
        except Exception:
            full_html = None

    return render(request, "space_news/article.html", {"article": article, "full_html": full_html})