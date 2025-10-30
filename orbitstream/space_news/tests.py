from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup  
from space_news import views as v
import requests


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

class UtilsFunctionTests(TestCase):
    """Tests for functions in utils.py"""

    @patch("space_news.utils.bleach.clean")
    @patch("space_news.utils.BeautifulSoup")
    @patch("space_news.utils.Document")
    @patch("space_news.utils.requests.get")
    def test_fetch_full_html_happy_path(self, mock_get, MockDoc, MockSoup, mock_clean):
        """Test successful fetch, parsing, and cleaning"""
        mock_response = MagicMock(status_code=200, text="<p>Raw HTML</p>")
        mock_get.return_value = mock_response

        # Mock readability
        MockDoc.return_value.summary.return_value = "<p>Summary HTML</p> <div>Junk</div>"
        
        # Mock BeautifulSoup object (so we can check tag removal)
        mock_soup_obj = MagicMock()
        MockSoup.return_value = mock_soup_obj

        # Mock bleach
        mock_clean.return_value = "<p>Cleaned HTML</p>"

        result = utils.fetch_full_html("https://example.com")

        # Verify flow
        mock_get.assert_called_with(
            "https://example.com", 
            timeout=8, 
            headers={"User-Agent": "OrbitStream/1.0"}
        )
        mock_response.raise_for_status.assert_called_once()
        MockDoc.assert_called_with("Raw HTML")
        MockDoc.return_value.summary.assert_called_with(html_partial=True)
        
        # Verify cleaning
        MockSoup.assert_called_with("<p>Summary HTML</p> <div>Junk</div>", "lxml")
        mock_soup_obj.find_all.assert_called_once() # Check that we looked for junk tags
        mock_clean.assert_called_once() # Check that bleach was called
        
        self.assertEqual(result, "<p>Cleaned HTML</p>")

    @patch("space_news.utils.requests.get", side_effect=requests.exceptions.RequestException)
    def test_fetch_full_html_handles_request_exception(self, mock_get):
        """Test that network failures, timeouts, etc. return None"""
        self.assertIsNone(utils.fetch_full_html("https://example.com"))
        
    @patch("space_news.utils.requests.get")
    def test_fetch_full_html_handles_http_error(self, mock_get):
        """Test that 404, 500, etc. (non-200) statuses return None"""
        mock_response = MagicMock(status_code=404)
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
        mock_get.return_value = mock_response
        
        self.assertIsNone(utils.fetch_full_html("https://example.com"))

class ViewHelperTests(TestCase):
    """Tests for private helper functions in views.py"""

    def test_make_uid_stable_and_unique(self):
        """Test that _make_uid is stable (same input -> same output) and unique"""
        article1 = {
            "title": "My Test Article",
            "url": "https://example.com/a",
            "publishedAt": "2025-01-01T00:00:00Z"
        }
        article2 = {
            "title": "My Test Article",
            "url": "https://example.com/b", # Different URL
            "publishedAt": "2025-01-01T00:00:00Z"
        }
        
        uid1 = v._make_uid(article1)
        uid1_again = v._make_uid(article1)
        uid2 = v._make_uid(article2)
        
        self.assertEqual(uid1, uid1_again)
        self.assertNotEqual(uid1, uid2)
        self.assertTrue(uid1.startswith("my-test-article-"))

    def test_make_uid_handles_missing_data(self):
        """Test _make_uid gracefully handles missing title or url"""
        article_no_title = {
            "url": "https://example.com/a",
            "publishedAt": "2025-01-01T00:00:00Z"
        }
        article_no_url = {
            "title": "No URL Article",
            "publishedAt": "2025-01-01T00:00:00Z"
        }
        article_all_missing = {}
        
        self.assertTrue(v._make_uid(article_no_title).startswith("untitled-"))
        self.assertTrue(v._make_uid(article_no_url).startswith("no-url-article-"))
        self.assertTrue(v._make_uid(article_all_missing).startswith("article-"))

    def test_remove_duplicates(self):
        """Test duplicate removal by URL and partial title"""
        articles = [
            {"title": "Article 1", "url": "https://example.com/1"},
            {"title": "Article 2", "url": "https://example.com/2"},
            {"title": "Article 1", "url": "https://example.com/1"}, # Duplicate URL
            {"title": "Article 3: A Long Title Here", "url": "https://example.com/3"},
            {"title": "Article 3: A Long Title Here and more", "url": "https://example.com/4"}, # Duplicate title prefix
        ]
        unique = v._remove_duplicates(articles)
        self.assertEqual(len(unique), 3)
        self.assertEqual(unique[0]['title'], "Article 1")
        self.assertEqual(unique[1]['title'], "Article 2")
        self.assertEqual(unique[2]['title'], "Article 3: A Long Title Here")

    @patch("space_news.views.RELIABLE_IMAGE_SOURCES", ["nasa.gov", "space.com"])
    def test_prioritize_sources(self, _mock_reliable):
        """Test that reliable sources are moved to the front"""
        articles = [
            {"title": "Regular 1", "url": "https://other.com/1", "source": {"name": "Other"}},
            {"title": "NASA Article", "url": "https://nasa.gov/1", "source": {"name": "NASA"}},
            {"title": "Regular 2", "url": "https://another.com/1", "source": {"name": "Another"}},
            {"title": "Space.com Article", "url": "https://foo.com/1", "source": {"name": "Space.com"}},
        ]
        prioritized = v._prioritize_sources(articles)
        self.assertEqual(len(prioritized), 4)
        self.assertEqual(prioritized[0]['title'], "NASA Article")
        self.assertEqual(prioritized[1]['title'], "Space.com Article")
        self.assertEqual(prioritized[2]['title'], "Regular 1")
        self.assertEqual(prioritized[3]['title'], "Regular 2")

    def test_is_excluded_domain(self):
        """Test domain exclusion logic"""
        excluded = ["bad.com", "worse.net"]
        self.assertTrue(v._is_excluded_domain("https://sub.bad.com/story", excluded))
        self.assertTrue(v._is_excluded_domain("https://worse.net/article", excluded))
        self.assertFalse(v._is_excluded_domain("https://good.com/story", excluded))
        self.assertFalse(v._is_excluded_domain(None, excluded))