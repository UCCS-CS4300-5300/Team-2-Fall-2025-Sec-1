from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import patch, Mock, MagicMock
from bs4 import BeautifulSoup  
from space_news import views as v
from datetime import datetime


class BasicUtilsTests(TestCase):
    def test_clean_image_url_filters_invalid(self):
        self.assertIsNone(v._clean_image_url("ftp://invalid"))
        self.assertIsNotNone(v._clean_image_url("https://example.com/image.jpg"))

    @patch("space_news.views.requests.head")
    def test_image_is_fetchable(self, mock_head):
        mock_head.return_value = MagicMock(status_code=200, headers={"Content-Type": "image/jpeg"})
        self.assertTrue(v._image_is_fetchable("https://cdn.test/img.jpg"))


class NASAViewTests(TestCase):
    @patch("space_news.views._image_is_fetchable", return_value=True)
    @patch("space_news.views.NewsApiClient")
    def test_nasa_news_filters_imageless(self, MockClient, _mock_fetchable):
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
        # should only include the one with a valid image
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

    # REMOVING ADMIN SECTION FOR NOW

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

        # Seed cache with article (no full_html yet)
        cache.set(
            "space_news_articles_by_uid",
            {uid: {"uid": uid, "title": "T", "url": article_url, "urlToImage": "https://img/ex.jpg"}},
            timeout=600,
        )

        # 1st GET: main page (contains amphtml link)
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

        # 2nd GET: amp page (returns actual content we keep)
        amp_html = "<article><p>AMP content OK</p></article>"
        resp_amp = MagicMock(status_code=200, text=amp_html)

        mock_get.side_effect = [resp_main, resp_amp]

        # Make Document(...).summary(...) return something that cleans to empty
        MockDoc.return_value.summary.return_value = "<div></div>"  # no text after cleaning

        # Hit the view
        r = self.client.get(f"/news/article/{uid}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"AMP content OK", r.content)

        # And it should have cached full_html now
        cached = cache.get("space_news_articles_by_uid")[uid]
        self.assertIn("full_html", cached)
        self.assertIn("AMP content OK", cached["full_html"])


# Mock NASA API JSON repsonses
APOD_IMAGE_JSON = {
    "date": "2025-10-29",
    "title": "Pretty Nebula",
    "explanation": "Space is pretty.",
    "media_type": "image",
    "url": "https://example.com/lo.jpg",
    "hdurl": "https://example.com/hi.jpg",
    "copyright": "NASA",
}

APOD_VIDEO_JSON = {
    "date": "2025-10-29",
    "title": "Cool Video",
    "explanation": "Space is cool.",
    "media_type": "video",
    "url": "https://www.youtube.com/embed/demo",
    "thumbnail_url": "https://example.com/thumb.jpg",
}

#Tests the fetch_apod() helper - calls NASA's APOD API caching the result and returning normalized fields
@override_settings(NASA_API_KEY="test-key")
@patch("space_news.views.requests.get")
class FetchApodTests(TestCase):
    def setUp(self):
        cache.clear()

    # Returns image-type data. Ensures HDURL instead of normal URL
    def test_fetches_and_returns_image_data(self, mock_get):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json.return_value = APOD_IMAGE_JSON
        mock_get.return_value = resp

        apod = v.fetch_apod()
        self.assertIsNotNone(apod)
        self.assertEqual(apod["media_type"], "image")
        self.assertEqual(apod["url"], APOD_IMAGE_JSON["hdurl"])  # prefers HD

    # Returns video-type data. Ensures URL points to actual video link
    def test_fetches_and_returns_video_data(self, mock_get):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json.return_value = APOD_VIDEO_JSON
        mock_get.return_value = resp

        apod = v.fetch_apod()
        self.assertIsNotNone(apod)
        self.assertEqual(apod["media_type"], "video")
        self.assertEqual(apod["url"], APOD_VIDEO_JSON["url"])

    # Cache the APOD result for one hour. Second call must not trigger another network request
    def test_caches_result_to_prevent_multiple_requests(self, mock_get):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json.return_value = APOD_IMAGE_JSON
        mock_get.return_value = resp

        a1 = v.fetch_apod()
        a2 = v.fetch_apod()  # should hit cache, not call API again
        self.assertEqual(a1, a2)
        mock_get.assert_called_once() #only the first call hits the API

# Ensures fetch_apod() safely returns None if no API key is found
@override_settings(NASA_API_KEY=None)
class FetchApodNoKeyTests(TestCase):
    def test_returns_none_without_api_key(self):
        cache.clear()
        self.assertIsNone(v.fetch_apod())

# Ensures fetch_apod() handles network or API errors gracefully by returning None
@override_settings(NASA_API_KEY="test-key")
@patch("space_news.views.requests.get")
class FetchApodErrorTests(TestCase):
    def test_returns_none_on_network_error(self, mock_get):
        mock_get.side_effect = Exception("boom") #simulate connection error
        self.assertIsNone(v.fetch_apod())


#nasa_news: images_only=0 keeps imageless
@override_settings(NEWS_API_KEY="news-key", NASA_API_KEY="nasa-key")
@patch("space_news.views.fetch_apod", return_value=None)
@patch("space_news.views.NewsApiClient")
class NasaNewsImagesOnlyOffTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    @patch("space_news.views._image_is_fetchable", return_value=False)
    def test_images_only_0_keeps_imageless(self, _m_fetchable, mnews, _m_apod):
        mclient = mnews.return_value
        mclient.get_everything.return_value = {
            "status": "ok",
            "articles": [{
                "title": "No image but allowed",
                "description": "space",
                "content": "rocket",
                "url": "https://news.example.com/b",
                "urlToImage": None,
                "publishedAt": "2025-10-24T00:00:00Z",
                "source": {"name": "Example"},
            }],
        }
        r = self.client.get("/news/?images_only=0")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"No image but allowed", r.content)

#APOD error banner when APOD missing/empty URL
@override_settings(NEWS_API_KEY="news-key", NASA_API_KEY="nasa-key")
@patch("space_news.views.fetch_apod", return_value={"title": "Bad APOD", "url": None, "media_type": "image"})
@patch("space_news.views.NewsApiClient")
class ApodErrorBannerTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_apod_error_message_visible(self, mnews, _m_apod):
        mclient = mnews.return_value
        mclient.get_everything.return_value = {"status": "ok", "articles": []}
        r = self.client.get("/news/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Astronomy Picture of the Day is unavailable", r.content)


#_image_is_fetchable caching: second call should not re-HEAD
class ImageIsFetchableCacheTests(TestCase):
    @patch("space_news.views.requests.head")
    def test_probe_is_cached(self, mhead):
        cache.clear()
        mhead.return_value = Mock(status_code=200, headers={"Content-Type": "image/png"})
        url = "https://cdn.test/img.png"
        self.assertTrue(v._image_is_fetchable(url))
        self.assertTrue(v._image_is_fetchable(url))  # cached
        self.assertEqual(mhead.call_count, 1)

# _make_uid: stable + slug + 8-char hash
class MakeUidTests(TestCase):
    def test_stable_and_slug_safe(self):
        art = {"title": "Hello World! 🚀", "url": "https://e/x", "publishedAt": "2025-10-29"}
        uid1 = v._make_uid(art)
        uid2 = v._make_uid(art)
        self.assertEqual(uid1, uid2)
        slug, dash, suffix = uid1.rpartition("-")
        self.assertTrue(dash)
        self.assertEqual(len(suffix), 8)
        self.assertTrue(slug)  # has slug part

#_remove_duplicates: by url and title
class RemoveDuplicatesTests(TestCase):
    def test_dedup_by_url_and_title(self):
        articles = [
            {"title": "A thing", "url": "https://e/x"},
            {"title": "A thing", "url": "https://e/x"},  # duplicate url
            {"title": "A thing", "url": "https://e/y"},  # duplicate title
            {"title": "Different", "url": "https://e/z"},
        ]
        deduped = v._remove_duplicates(articles)
        self.assertEqual(len(deduped), 2)
        titles = {a["title"] for a in deduped}
        self.assertEqual(titles, {"A thing", "Different"})

# article_detail: 404 when not cached
class ArticleDetailNotFoundTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_404_for_missing_uid(self):
        r = self.client.get("/news/article/does-not-exist/")
        self.assertEqual(r.status_code, 404)

# nasa_news: handles NewsAPI failure status
@override_settings(NEWS_API_KEY="news-key", NASA_API_KEY="nasa-key")
@patch("space_news.views.fetch_apod", return_value=None)
@patch("space_news.views.NewsApiClient")
class NasaNewsFailurePathTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_newsapi_status_not_ok_sets_error(self, mnews, _m_apod):
        mclient = mnews.return_value
        mclient.get_everything.return_value = {"status": "error", "message": "boom"}
        r = self.client.get("/news/")
        self.assertEqual(r.status_code, 200)
        # page renders; no crash; shows 0 articles
        self.assertIn(b"NASA Space News", r.content)
        # template may or may not surface the exact error text, but context should have no articles
        self.assertEqual(r.context["total_results"], 0)

# article_detail: uses cached full_html (no network)
class ArticleDetailUsesCachedHtmlTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    @patch("space_news.views.requests.get")
    def test_renders_from_cache_without_network(self, mget):
        uid = "cached-uid-aaaa1111"
        article = {
            "uid": uid,
            "title": "Cached Article",
            "url": "https://news.example.com/cached",
            "urlToImage": "https://img.example.com/cached.jpg",
            "full_html": "<p>Cached content only.</p>",
        }
        cache.set("space_news_articles_by_uid", {uid: article}, timeout=600)

        r = self.client.get(f"/news/article/{uid}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Cached content only.", r.content)
        mget.assert_not_called()  # no network if full_html already cached

# _image_is_fetchable: HEAD says not image, GET says image -> True
class ImageIsFetchableHeadThenGetTests(TestCase):
    @patch("space_news.views.requests.get")
    @patch("space_news.views.requests.head")
    def test_head_non_image_then_get_image(self, mhead, mget):
        cache.clear()
        # HEAD returns 200 but non-image content-type
        mhead.return_value = Mock(status_code=200, headers={"Content-Type": "text/html"})
        # GET returns 200 with image content-type
        mget.return_value = Mock(status_code=200, headers={"Content-Type": "image/jpeg"})

        url = "https://cdn.test/fallback.jpg"
        self.assertTrue(v._image_is_fetchable(url))
        # both were used
        self.assertEqual(mhead.call_count, 1)
        self.assertEqual(mget.call_count, 1)
