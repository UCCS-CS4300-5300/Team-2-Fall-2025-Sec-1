# space_news/views.py
from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from django.http import Http404
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

    apod = None
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