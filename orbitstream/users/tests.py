from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
# Create your tests here.
# users/tests.py

User = get_user_model()

class AuthViewsTests(TestCase):
    def setUp(self):
        # Existing user for login tests
        self.password = "s3cret123!"
        self.user = User.objects.create_user(username="alice", password=self.password)

    # ---------- LOGIN ----------
    def test_login_template_renders(self):
        resp = self.client.get(reverse("users:login_view"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "users/login.html")
        # AuthenticationForm exposes username/password fields
        self.assertIn("form", resp.context)

    def test_login_success_redirects_and_authenticates(self):
        resp = self.client.post(
            reverse("users:login_view"),
            {"username": "alice", "password": self.password, "next": reverse("index")},
        )
        self.assertRedirects(resp, reverse("index"))
        # user is now authenticated in the session
        # do a follow-up GET to confirm template context user is authenticated
        resp2 = self.client.get(reverse("index"))
        self.assertTrue(resp2.context["user"].is_authenticated)

    def test_login_failure_shows_non_field_errors(self):
        resp = self.client.post(reverse("users:login_view"), {"username": "alice", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        # Non-field errors live under __all__
        form = resp.context["form"]
        self.assertTrue(form.errors.get("__all__"))  # e.g., "Please enter a correct username and password."

    # ---------- REGISTRATION (UserCreationForm-like) ----------
    def test_register_success_creates_user_and_redirects(self):
        resp = self.client.post(
            reverse("users:register_view"),
            {
                "username": "bob",
                "password1": "Another$tr0ngPass1",
                "password2": "Another$tr0ngPass1",
            },
        )

        # On success your view should redirect (e.g., to login or index)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="bob").exists())

    def test_register_password_mismatch_shows_error(self):
        resp = self.client.post(
            reverse("users:register_view"),
            {
                "username": "carol",
                "password1": "Mismatch123$",
                "password2": "Mismatch321$",
            },
        )
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        # Default UserCreationForm puts mismatch on 'password2'
        self.assertTrue(form.errors.get("password2"))

    # ---------- LOGOUT ----------
    def test_logout_requires_post(self):
        # Using your @require_POST logout view should 405 on GET
        resp = self.client.get(reverse("users:logout_view"))
        self.assertEqual(resp.status_code, 405)

    def test_logout_post_logs_out_and_redirects(self):
        # Log the user in first
        self.client.login(username="alice", password=self.password)

        resp = self.client.post(reverse("users:logout_view"), data={"next": reverse("index")})
        self.assertRedirects(resp, reverse("index"))

        # After logout, user should no longer be authenticated
        resp2 = self.client.get(reverse("index"))
        self.assertFalse(resp2.context["user"].is_authenticated)

    # ---------- NEXT param honored on login ----------
    def test_login_honors_next_param(self):
        target = reverse("index")  
        resp = self.client.post(
            reverse("users:login_view"),
            {"username": "alice", "password": self.password, "next": target},
        )
        self.assertRedirects(resp, target)
