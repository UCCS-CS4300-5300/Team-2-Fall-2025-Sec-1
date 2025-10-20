from django.test import TestCase

class URLCoverageTest(TestCase):
    def test_home_page_url(self):
        resp = self.client.get("/")                 # index
        self.assertEqual(resp.status_code, 200)

    def test_space_news_list_url(self):
        resp = self.client.get("/news/")            # space_news root include
        # If this view calls an external API, it might 500 in CI unless you mock.
        # For a pure smoke test you can assert it's not a 404:
        # self.assertNotEqual(resp.status_code, 404)
        self.assertEqual(resp.status_code, 200)

    def test_admin_url_redirects_to_login(self):
        resp = self.client.get("/admin/")           # unauthenticated → redirect
        self.assertEqual(resp.status_code, 302)
        # Optionally follow and assert final page is reachable:
        resp = self.client.get("/admin/", follow=True)
        self.assertEqual(resp.status_code, 200)
        # And the redirect chain points to admin login:
        self.assertTrue(any("/admin/login/" in url for (url, code) in resp.redirect_chain))