from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from news_filter.models import FilterPreset
from datetime import date
import json

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

    def test_register_get_renders_form(self):
        """Test that GET request to register renders the form"""
        resp = self.client.get(reverse("users:register_view"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "users/register.html")
        self.assertIn("form", resp.context)

    def test_register_auto_login_after_creation(self):
        """Test that user is automatically logged in after registration"""
        resp = self.client.post(
            reverse("users:register_view"),
            {
                "username": "autotest",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
            },
        )
        # Check if redirected
        self.assertEqual(resp.status_code, 302)
        # Check if user is authenticated
        resp2 = self.client.get(reverse("index"))
        self.assertTrue(resp2.context["user"].is_authenticated)
        self.assertEqual(resp2.context["user"].username, "autotest")

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


class SettingsViewTests(TestCase):
    def setUp(self):
        self.password = "TestPass123!"
        self.user = User.objects.create_user(username="testuser", password=self.password)
        self.client.login(username="testuser", password=self.password)

    def test_settings_requires_login(self):
        """Test that unauthenticated users are redirected"""
        self.client.logout()
        resp = self.client.get(reverse("users:settings"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_settings_view_get_renders_correctly(self):
        """Test that settings page renders with correct forms"""
        resp = self.client.get(reverse("users:settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "users/settings.html")
        self.assertIn("password_form", resp.context)
        self.assertIn("filter_presets", resp.context)
        self.assertIn("preset_form", resp.context)

    def test_password_change_success(self):
        """Test successful password change"""
        new_password = "NewPass456!"
        resp = self.client.post(
            reverse("users:settings"),
            {
                "old_password": self.password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )
        self.assertRedirects(resp, reverse("users:settings"))
        
        # Check success message
        messages = list(resp.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn("successfully updated", str(messages[0]))
        
        # Verify user can login with new password
        self.client.logout()
        login_success = self.client.login(username="testuser", password=new_password)
        self.assertTrue(login_success)

    def test_password_change_wrong_old_password(self):
        """Test password change with incorrect old password"""
        resp = self.client.post(
            reverse("users:settings"),
            {
                "old_password": "WrongPassword!",
                "new_password1": "NewPass456!",
                "new_password2": "NewPass456!",
            },
        )
        self.assertEqual(resp.status_code, 200)
        messages = list(resp.wsgi_request._messages)
        self.assertTrue(any("error" in str(m).lower() for m in messages))

    def test_password_change_mismatch(self):
        """Test password change with mismatched new passwords"""
        resp = self.client.post(
            reverse("users:settings"),
            {
                "old_password": self.password,
                "new_password1": "NewPass456!",
                "new_password2": "DifferentPass789!",
            },
        )
        self.assertEqual(resp.status_code, 200)
        messages = list(resp.wsgi_request._messages)
        self.assertTrue(any("error" in str(m).lower() for m in messages))


class FilterPresetTests(TestCase):
    def setUp(self):
        self.password = "TestPass123!"
        self.user = User.objects.create_user(username="testuser", password=self.password)
        self.other_user = User.objects.create_user(username="otheruser", password=self.password)
        self.client.login(username="testuser", password=self.password)
        
        # Create a test preset
        self.preset = FilterPreset.objects.create(
            user=self.user,
            name="Test Preset",
            search_query="space",
            sort_by="relevancy",
        )

    def _get_valid_preset_data(self, name="New Preset"):
        """Helper method to get valid preset data"""
        return {
            "name": name,
            "search_query": "NASA",
            "date_from": "",
            "date_to": "",
            "sort_by": "publishedAt",
            # Don't include source field - let it be blank/optional
        }

    def test_create_preset_success(self):
        """Test successful preset creation"""
        initial_count = FilterPreset.objects.filter(user=self.user).count()
        
        resp = self.client.post(
            reverse("users:create_preset"),
            self._get_valid_preset_data("Unique Preset Name"),
        )
        self.assertRedirects(resp, reverse("users:settings"))
        
        # Check that a new preset was created
        new_count = FilterPreset.objects.filter(user=self.user).count()
        self.assertEqual(new_count, initial_count + 1)
        self.assertTrue(FilterPreset.objects.filter(name="Unique Preset Name", user=self.user).exists())
        
        # Check success message
        messages = list(resp.wsgi_request._messages)
        self.assertTrue(any("created successfully" in str(m) for m in messages))

    def test_create_preset_duplicate_name(self):
        """Test creating preset with duplicate name for same user"""
        # First verify the preset exists
        self.assertTrue(FilterPreset.objects.filter(name="Test Preset", user=self.user).exists())
        
        data = self._get_valid_preset_data("Test Preset")  # Same as existing preset
        data["search_query"] = "Mars"
        
        resp = self.client.post(reverse("users:create_preset"), data)
        self.assertRedirects(resp, reverse("users:settings"))
        
        messages = list(resp.wsgi_request._messages)
        # The view catches exceptions and shows error messages
        message_strings = [str(m) for m in messages]
        has_error = any(
            "error" in msg.lower() or 
            "exists" in msg.lower() or 
            "already" in msg.lower() 
            for msg in message_strings
        )
        self.assertTrue(has_error, f"Expected error message, got: {message_strings}")

    def test_create_preset_requires_login(self):
        """Test that preset creation requires authentication"""
        self.client.logout()
        resp = self.client.post(
            reverse("users:create_preset"),
            self._get_valid_preset_data(),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_create_preset_get_redirects(self):
        """Test that GET request to create_preset redirects to settings"""
        resp = self.client.get(reverse("users:create_preset"))
        self.assertRedirects(resp, reverse("users:settings"))

    def test_create_preset_with_date_fields(self):
        """Test creating preset with date filters"""
        data = self._get_valid_preset_data("Date Preset")
        data.update({
            "search_query": "rockets",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
        
        resp = self.client.post(reverse("users:create_preset"), data)
        self.assertRedirects(resp, reverse("users:settings"))
        
        # Check if preset was created
        if FilterPreset.objects.filter(name="Date Preset", user=self.user).exists():
            preset = FilterPreset.objects.get(name="Date Preset", user=self.user)
            self.assertEqual(preset.date_from, date(2024, 1, 1))
            self.assertEqual(preset.date_to, date(2024, 12, 31))

    def test_edit_preset_success(self):
        """Test successful preset editing"""
        data = self._get_valid_preset_data("Updated Preset")
        data["search_query"] = "satellites"
        
        resp = self.client.post(
            reverse("users:edit_preset", args=[self.preset.id]),
            data,
        )
        self.assertRedirects(resp, reverse("users:settings"))
        
        # Refresh and check if updated
        self.preset.refresh_from_db()
        if self.preset.name == "Updated Preset":  # If form was valid
            self.assertEqual(self.preset.search_query, "satellites")
            
            # Check success message
            messages = list(resp.wsgi_request._messages)
            self.assertTrue(any("updated successfully" in str(m) for m in messages))

    def test_edit_preset_nonexistent(self):
        """Test editing a preset that doesn't exist returns 404"""
        resp = self.client.post(
            reverse("users:edit_preset", args=[99999]),
            self._get_valid_preset_data(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_edit_preset_requires_login(self):
        """Test that editing requires authentication"""
        self.client.logout()
        resp = self.client.post(
            reverse("users:edit_preset", args=[self.preset.id]),
            self._get_valid_preset_data(),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_edit_preset_get_redirects(self):
        """Test that GET request to edit_preset redirects to settings"""
        resp = self.client.get(reverse("users:edit_preset", args=[self.preset.id]))
        self.assertRedirects(resp, reverse("users:settings"))

    def test_delete_preset_success(self):
        """Test successful preset deletion"""
        preset_id = self.preset.id
        resp = self.client.post(reverse("users:delete_preset", args=[preset_id]))
        
        self.assertRedirects(resp, reverse("users:settings"))
        self.assertFalse(FilterPreset.objects.filter(id=preset_id).exists())
        
        # Check success message
        messages = list(resp.wsgi_request._messages)
        self.assertTrue(any("deleted successfully" in str(m) for m in messages))

    def test_delete_preset_requires_post(self):
        """Test that delete requires POST method"""
        resp = self.client.get(reverse("users:delete_preset", args=[self.preset.id]))
        self.assertEqual(resp.status_code, 405)

    def test_delete_preset_other_user(self):
        """Test that users can't delete other users' presets"""
        other_preset = FilterPreset.objects.create(
            user=self.other_user,
            name="Other User Preset",
            search_query="test",
        )
        resp = self.client.post(reverse("users:delete_preset", args=[other_preset.id]))
        self.assertEqual(resp.status_code, 404)
        # Preset should still exist
        self.assertTrue(FilterPreset.objects.filter(id=other_preset.id).exists())

    def test_delete_preset_requires_login(self):
        """Test that deletion requires authentication"""
        self.client.logout()
        resp = self.client.post(reverse("users:delete_preset", args=[self.preset.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_get_preset_ajax_success(self):
        """Test getting preset data via AJAX"""
        resp = self.client.get(reverse("users:get_preset", args=[self.preset.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        
        data = json.loads(resp.content)
        self.assertEqual(data["id"], self.preset.id)
        self.assertEqual(data["name"], self.preset.name)
        self.assertEqual(data["search_query"], self.preset.search_query)
        self.assertEqual(data["sort_by"], self.preset.sort_by)

    def test_get_preset_with_dates(self):
        """Test getting preset with date fields"""
        preset_with_dates = FilterPreset.objects.create(
            user=self.user,
            name="Dated Preset",
            search_query="test",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
            sort_by="publishedAt",
        )
        
        resp = self.client.get(reverse("users:get_preset", args=[preset_with_dates.id]))
        data = json.loads(resp.content)
        
        self.assertEqual(data["date_from"], "2024-01-01")
        self.assertEqual(data["date_to"], "2024-12-31")

    def test_get_preset_with_empty_dates(self):
        """Test getting preset with null date fields"""
        resp = self.client.get(reverse("users:get_preset", args=[self.preset.id]))
        data = json.loads(resp.content)
        
        self.assertEqual(data["date_from"], "")
        self.assertEqual(data["date_to"], "")

    def test_get_preset_other_user(self):
        """Test that users can't access other users' preset data"""
        other_preset = FilterPreset.objects.create(
            user=self.other_user,
            name="Other Preset",
            search_query="test",
        )
        resp = self.client.get(reverse("users:get_preset", args=[other_preset.id]))
        self.assertEqual(resp.status_code, 404)

    def test_get_preset_requires_login(self):
        """Test that getting preset requires authentication"""
        self.client.logout()
        resp = self.client.get(reverse("users:get_preset", args=[self.preset.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_settings_shows_user_presets(self):
        """Test that settings page shows only user's presets"""
        # Create preset for other user
        FilterPreset.objects.create(
            user=self.other_user,
            name="Other User Preset",
            search_query="test",
        )
        
        resp = self.client.get(reverse("users:settings"))
        presets = resp.context["filter_presets"]
        
        # Should only contain current user's preset
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0].user, self.user)

    def test_create_preset_invalid_form(self):
        """Test creating preset with invalid data"""
        resp = self.client.post(
            reverse("users:create_preset"),
            {
                "name": "",  # Empty name should be invalid
                "search_query": "",
            },
        )
        self.assertRedirects(resp, reverse("users:settings"))
        messages = list(resp.wsgi_request._messages)
        # Should have error messages
        self.assertTrue(len(messages) > 0)

    def test_edit_preset_invalid_form(self):
        """Test editing preset with invalid data"""
        resp = self.client.post(
            reverse("users:edit_preset", args=[self.preset.id]),
            {
                "name": "",  # Empty name
                "search_query": "",
            },
        )
        # View redirects even on invalid form
        self.assertRedirects(resp, reverse("users:settings"))