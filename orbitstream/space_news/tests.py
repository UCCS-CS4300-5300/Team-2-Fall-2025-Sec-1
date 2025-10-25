from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup  
from space_news import views as v


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
