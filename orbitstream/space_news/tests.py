from django.test import Client, TestCase
from django.urls import reverse

from unittest.mock import patch, MagicMock
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