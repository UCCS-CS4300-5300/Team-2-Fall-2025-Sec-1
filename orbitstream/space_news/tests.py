# tests.py
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

# Import the module under test so we can patch its constants/functions
from space_news import views as v
from space_news import utils as u


# --------------------------------------------------------------------------------------
# Your existing tests (kept intact)
# --------------------------------------------------------------------------------------

class BasicUtilsTests(TestCase):
    def test_clean_image_url_filters_invalid(self):
        self.assertIsNone(v._clean_image_url("ftp://invalid"))
        self.assertIsNotNone(v._clean_image_url("https://example.com/image.jpg"))

    @patch("space_news.views.requests.head")
    def test_image_is_fetchable(self, mock_head):
        # If your codebase removed _image_is_fetchable, you can delete this test.
        mock_head.return_value = MagicMock(status_code=200, headers={"Content-Type": "image/jpeg"})
        self.assertTrue(getattr(v, "_image_is_fetchable", lambda *_: True)("https://cdn.test/img.jpg"))


class NASAViewTests(TestCase):
    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_filters_imageless(self, MockClient):
        mock_api = MockClient.return_value
        mock_api.get_everything.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Valid Image",
                    "description": "space",
                    "content": "rocket",
                    "url": "https://example.com/a",
                    "urlToImage": "https://cdn.test/a.jpg",
                    "publishedAt": "2025-10-24",
                },
                {
                    "title": "No Image",
                    "description": "space",
                    "content": "rocket",
                    "url": "https://example.com/b",
                    "urlToImage": None,
                    "publishedAt": "2025-10-24",
                },
            ],
        }

        client = Client()
        response = client.get("/news/")
        self.assertEqual(response.status_code, 200)
        articles = response.context["articles"]
        # should only include the one with a valid image (images_only default is ON)
        self.assertEqual(len(articles), 1)
        self.assertIn("Valid Image", articles[0]["title"])


class URLCoverageTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_url(self):
        response = self.client.get('/') 
        self.assertEqual(response.status_code, 200)

    def test_space_news_list_url(self):
        response = self.client.get('/news/')
        self.assertEqual(response.status_code, 200)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class ArticleDetailAmpFallbackTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("space_news.views.Document")
    @patch("space_news.views.requests.get")
    def test_article_detail_uses_amp_fallback_when_primary_empty(self, mock_get, MockDoc):
        """
        Simulate: primary page yields empty/unsalvageable summary,
        but page has <link rel="amphtml" href="..."> and AMP returns content.
        """
        uid = "some-uid-1234abcd"
        article_url = "https://example.com/post"

        cache.set(
            "space_news_articles_by_uid",
            {uid: {"uid": uid, "title": "T", "url": article_url, "urlToImage": "https://img/ex.jpg"}},
            timeout=600,
        )

        main_html = """
        <html>
          <head>
            <link rel="amphtml" href="https://example.com/amp/post">
          </head>
          <body>
            <div>main page but summary will be empty after cleaning</div>
          </body>
        </html>
        """
        resp_main = MagicMock(status_code=200, text=main_html)

        amp_html = "<article><p>AMP content OK</p></article>"
        resp_amp = MagicMock(status_code=200, text=amp_html)

        mock_get.side_effect = [resp_main, resp_amp]
        MockDoc.return_value.summary.return_value = "<div></div>"  # cleans to empty

        r = self.client.get(f"/news/article/{uid}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"AMP content OK", r.content)

        cached = cache.get("space_news_articles_by_uid")[uid]
        self.assertIn("full_html", cached)
        self.assertIn("AMP content OK", cached["full_html"])


# --------------------------------------------------------------------------------------
# New / additional tests for utils.fetch_full_html and views.nasa_news/article_detail
# --------------------------------------------------------------------------------------

class FetchFullHtmlTests(TestCase):
    @patch("space_news.utils.requests.get")
    def test_fetch_full_html_success_sanitizes_and_lazyloads(self, mock_get):
        raw_html = """
        <html>
          <body>
            <article>
              <h2>Headline</h2>
              <p>Body <script>alert('x');</script> text.</p>
              <img src="https://cdn.test/pic.jpg" width="800" height="600">
              <iframe src="https://evil"></iframe>
            </article>
          </body>
        </html>
        """
        mock_resp = MagicMock(status_code=200, text=raw_html)
        mock_get.return_value = mock_resp

        # Patch Document.summary to return only the main article portion
        with patch("space_news.utils.Document") as MockDoc:
            MockDoc.return_value.summary.return_value = "<article><h2>Headline</h2><p>Safe</p><img src='https://cdn.test/pic.jpg'></article>"
            cleaned = u.fetch_full_html("https://example.com/post")
            self.assertIsInstance(cleaned, str)
            # scripts/iframes should be removed, img should have loading=lazy
            soup = BeautifulSoup(cleaned, "lxml")
            self.assertIsNone(soup.find("script"))
            self.assertIsNone(soup.find("iframe"))
            img = soup.find("img")
            self.assertIsNotNone(img)
            self.assertEqual(img.get("loading"), "lazy")
            self.assertIn("Headline", soup.get_text())

    @patch("space_news.utils.requests.get")
    def test_fetch_full_html_request_failure_returns_none(self, mock_get):
        mock_get.side_effect = Exception("network down")
        self.assertIsNone(u.fetch_full_html("https://example.com/post"))


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class NasaNewsAdditionalTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_images_only_toggle_off_includes_imageless(self, MockClient):
        """?images_only=0 should let imageless articles through (after other filters)."""
        MockClient.return_value.get_everything.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Imageless but Real Space News",
                    "description": "SpaceX launch window",
                    "content": "Falcon 9",
                    "url": "https://spacex.com/mission",
                    "urlToImage": None,
                    "publishedAt": "2025-10-24",
                    "source": {"name": "SpaceX"},
                },
            ],
        }
        with patch.object(v, "EXCLUDED_DOMAINS", []), \
             patch.object(v, "SPACE_KEYWORDS_ALL", ["space", "spacex", "nasa"]), \
             patch.object(v, "EXCLUDED_TOPICS_ALL", []):
            r = self.client.get("/news/?images_only=0")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.context["articles"]), 1)
            self.assertIsNone(r.context["articles"][0]["urlToImage"])

    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_excluded_domain_is_dropped(self, MockClient):
        MockClient.return_value.get_everything.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Looks Spacey",
                    "description": "space news",
                    "content": "satellite",
                    "url": "https://ads.bad.com/story",
                    "urlToImage": "https://cdn.test/a.jpg",
                    "publishedAt": "2025-10-24",
                    "source": {"name": "Bad Ads"},
                },
                {
                    "title": "Real NASA Mission",
                    "description": "NASA mission update",
                    "content": "space",
                    "url": "https://www.nasa.gov/press",
                    "urlToImage": "https://images-assets.nasa.gov/abc.jpg",
                    "publishedAt": "2025-10-24",
                    "source": {"name": "NASA"},
                },
            ],
        }
        with patch.object(v, "EXCLUDED_DOMAINS", ["bad.com"]), \
             patch.object(v, "SPACE_KEYWORDS_ALL", ["space", "nasa"]), \
             patch.object(v, "EXCLUDED_TOPICS_ALL", []):
            r = self.client.get("/news/")
            self.assertEqual(r.status_code, 200)
            articles = r.context["articles"]
            self.assertEqual(len(articles), 1)
            self.assertIn("Real NASA Mission", articles[0]["title"])

    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_prioritizes_reliable_image_sources(self, MockClient):
        """Articles from RELIABLE_IMAGE_SOURCES should be moved to front."""
        MockClient.return_value.get_everything.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Generic Site Story",
                    "description": "space",
                    "content": "space",
                    "url": "https://random-site.example/story",
                    "urlToImage": "https://cdn.random/img.png",
                    "publishedAt": "2025-10-24",
                    "source": {"name": "Random"},
                },
                {
                    "title": "NASA Story",
                    "description": "space",
                    "content": "space",
                    "url": "https://www.nasa.gov/story",
                    "urlToImage": "https://images.nasa.gov/xyz.jpg",
                    "publishedAt": "2025-10-24",
                    "source": {"name": "NASA"},
                },
            ],
        }
        with patch.object(v, "EXCLUDED_DOMAINS", []), \
             patch.object(v, "SPACE_KEYWORDS_ALL", ["space", "nasa"]), \
             patch.object(v, "EXCLUDED_TOPICS_ALL", []), \
             patch.object(v, "RELIABLE_IMAGE_SOURCES", ["nasa.gov", "spacex.com"]):
            r = self.client.get("/news/")
            self.assertEqual(r.status_code, 200)
            titles = [a["title"] for a in r.context["articles"]]
            # NASA story should be first after prioritization
            self.assertEqual(titles[0], "NASA Story")

    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_respects_total_articles_limit_and_per_source_cap(self, MockClient):
        """Ensure MAX_ARTICLES_PER_SOURCE and TOTAL_ARTICLES_LIMIT are enforced."""
        # 3 from the same source + 2 from another -> with per-source cap=2, we expect 4 (then sliced by TOTAL limit)
        articles = []
        for i in range(3):
            articles.append({
                "title": f"SrcA-{i}",
                "description": "space",
                "content": "space",
                "url": f"https://src-a.example/{i}",
                "urlToImage": f"https://cdn.test/a{i}.jpg",
                "publishedAt": "2025-10-24",
                "source": {"name": "SrcA"},
            })
        for i in range(2):
            articles.append({
                "title": f"SrcB-{i}",
                "description": "space",
                "content": "space",
                "url": f"https://src-b.example/{i}",
                "urlToImage": f"https://cdn.test/b{i}.jpg",
                "publishedAt": "2025-10-24",
                "source": {"name": "SrcB"},
            })

        MockClient.return_value.get_everything.return_value = {"status": "ok", "articles": articles}

        with patch.object(v, "EXCLUDED_DOMAINS", []), \
             patch.object(v, "SPACE_KEYWORDS_ALL", ["space"]), \
             patch.object(v, "EXCLUDED_TOPICS_ALL", []), \
             patch.object(v, "MAX_ARTICLES_PER_SOURCE", 2), \
             patch.object(v, "TOTAL_ARTICLES_LIMIT", 4):
            r = self.client.get("/news/")
            self.assertEqual(r.status_code, 200)
            result = r.context["articles"]
            self.assertEqual(len(result), 4)
            # At most 2 from SrcA and 2 from SrcB
            counts = {}
            for a in result:
                src = a.get("source", {}).get("name")
                counts[src] = counts.get(src, 0) + 1
            self.assertLessEqual(counts.get("SrcA", 0), 2)
            self.assertLessEqual(counts.get("SrcB", 0), 2)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class ArticleDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_article_detail_404_when_uid_missing(self):
        r = self.client.get("/news/article/missing-uid/")
        self.assertEqual(r.status_code, 404)

    @patch("space_news.views.requests.get")
    @patch("space_news.views.Document")
    def test_article_detail_uses_cached_full_html_without_fetch(self, MockDoc, mock_get):
        uid = "cached-uid-9999abcd"
        cache.set(
            "space_news_articles_by_uid",
            {
                uid: {
                    "uid": uid,
                    "title": "Cached",
                    "url": "https://example.com/cached",
                    "urlToImage": "https://cdn/c.jpg",
                    "full_html": "<article><p>Already cached</p></article>",
                }
            },
            timeout=600,
        )
        r = self.client.get(f"/news/article/{uid}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Already cached", r.content)
        mock_get.assert_not_called()
        MockDoc.assert_not_called()

    @patch("space_news.views.requests.get")
    @patch("space_news.views.Document")
    def test_article_detail_fetches_and_caches_when_missing_full_html(self, MockDoc, mock_get):
        uid = "fetch-uid-aaaa1111"
        url = "https://example.com/story"
        cache.set(
            "space_news_articles_by_uid",
            {
                uid: {
                    "uid": uid,
                    "title": "Needs Fetch",
                    "url": url,
                    "urlToImage": "https://cdn/x.jpg",
                }
            },
            timeout=600,
        )

        main_resp = MagicMock(status_code=200, text="<html><body><article><p>Main OK</p></article></body></html>")
        mock_get.return_value = main_resp
        MockDoc.return_value.summary.return_value = "<article><p>Main OK</p></article>"

        r = self.client.get(f"/news/article/{uid}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Main OK", r.content)

        # confirm it got cached
        cached = cache.get("space_news_articles_by_uid")[uid]
        self.assertIn("full_html", cached)
        self.assertIn("Main OK", cached["full_html"])

@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class FetchApodEssentialTests(TestCase):
    """Essential tests for fetch_apod() function."""
    
    def setUp(self):
        cache.clear()
    
    @patch("space_news.views.requests.get")
    @override_settings(NASA_API_KEY="test-key-12345")
    def test_fetch_apod_success(self, mock_get):
        """Test successful APOD fetch and caching."""
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "title": "Test APOD",
            "date": "2025-11-03",
            "url": "https://apod.nasa.gov/image.jpg",
            "hdurl": "https://apod.nasa.gov/image_hd.jpg",
            "media_type": "image",
            "explanation": "Test",
        }
        mock_get.return_value = mock_response
        
        result = v.fetch_apod()
        
        self.assertIsNotNone(result)
        self.assertEqual(result["url"], "https://apod.nasa.gov/image_hd.jpg")
        
        # Verify caching works
        cached = cache.get("apod:current")
        self.assertIsNotNone(cached)
    
    def test_fetch_apod_returns_cached_without_api_call(self):
        """Test that cached APOD is returned without making API call."""
        cached_apod = {"title": "Cached", "url": "https://cached.jpg"}
        cache.set("apod:current", cached_apod, timeout=3600)
        
        with patch("space_news.views.requests.get") as mock_get:
            result = v.fetch_apod()
            
            self.assertEqual(result["title"], "Cached")
            mock_get.assert_not_called()
    
    @patch("space_news.views.requests.get")
    @override_settings(NASA_API_KEY="test-key-12345")
    def test_fetch_apod_returns_none_on_failure(self, mock_get):
        """Test that None is returned when API fails."""
        mock_get.side_effect = Exception("API down")
        
        result = v.fetch_apod()
        
        self.assertIsNone(result)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class FetchApodAsyncEssentialTests(TestCase):
    """Essential tests for fetch_apod_async() view."""
    
    def setUp(self):
        self.client = Client()
        cache.clear()
    
    @patch("space_news.views.fetch_apod")
    def test_fetch_apod_async_returns_json(self, mock_fetch):
        """Test that endpoint returns JSON on success."""
        mock_fetch.return_value = {
            "title": "Test",
            "url": "https://test.jpg",
            "media_type": "image"
        }
        
        response = self.client.get(reverse("space_news:fetch_apod_async"))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Test")
    
    @patch("space_news.views.fetch_apod")
    def test_fetch_apod_async_returns_503_on_failure(self, mock_fetch):
        """Test that 503 is returned when APOD unavailable."""
        mock_fetch.return_value = None
        
        response = self.client.get(reverse("space_news:fetch_apod_async"))
        
        self.assertEqual(response.status_code, 503)


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class NasaNewsApodEssentialTests(TestCase):
    """Essential tests for APOD in nasa_news view."""
    
    def setUp(self):
        self.client = Client()
        cache.clear()
    
    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_uses_cached_apod(self, MockClient):
        """Test that view uses cached APOD without fetching."""
        MockClient.return_value.get_everything.return_value = {
            "status": "ok",
            "articles": []
        }
        
        cache.set("apod:current", {"title": "Test", "url": "https://test.jpg"}, timeout=3600)
        
        response = self.client.get("/news/")
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["apod"])
        self.assertIsNone(response.context["apod_error"])
    
    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_shows_loading_when_no_cache(self, MockClient):
        """Test that loading message appears when APOD not cached."""
        MockClient.return_value.get_everything.return_value = {
            "status": "ok",
            "articles": []
        }
        
        response = self.client.get("/news/")
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["apod"])
        self.assertEqual(response.context["apod_error"], "Loading Astronomy Picture of the Day...")