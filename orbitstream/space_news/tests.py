
from django.test import Client, TestCase
from django.urls import reverse

class URLCoverageTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_url(self):
        response = self.client.get(reverse('index')) 
        self.assertEqual(response.status_code, 200)

    def test_space_news_list_url(self):
        response = self.client.get(reverse('nasa_news'))
        self.assertEqual(response.status_code, 200)

