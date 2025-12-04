"""
Tests for the launches app.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

from launches.api import spacedev_api


class SpaceDevAPITests(TestCase):
    """Test suite for SpaceDevs API functions."""

    def setUp(self):
        """Clear caches before each test."""
        # in-module cache (even though you're mostly using Django cache now)
        if hasattr(spacedev_api, "_cache"):
            spacedev_api._cache.clear()
        cache.clear()

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_next_launch_success(self, mock_get):
        """Test successful fetch of next launch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{
                "id": "test-123",
                "name": "Falcon 9 | Starlink",
                # far in the future so it always counts as 'upcoming'
                "net": "2050-11-20T10:30:00Z"
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_next_launch()

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "test-123")

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_next_launch_empty_results(self, mock_get):
        """Test handling of empty results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_next_launch()

        self.assertIsNone(result)

    @patch('launches.api.spacedev_api.requests.get')
    def test_spacedev_hero_success(self, mock_get):
        """Test hero data extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{
                "id": "hero-123",
                "name": "Mission Name",
                "net": "2050-11-20T10:00:00Z",
                "image": "https://example.com/img.jpg",
                "rocket": {"configuration": {"full_name": "Falcon 9"}},
                "pad": {"name": "Launch Pad", "location": {"name": "Location"}}
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.spacedev_hero()

        self.assertIsNotNone(result)
        self.assertEqual(result["mission_name"], "Mission Name")
        self.assertEqual(result["launch_id"], "hero-123")

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_upcoming_launches(self, mock_get):
        """
        Test fetching multiple upcoming launches.

        get_upcoming_launches(limit=3) should return 3 *future* launches,
        skipping the hero (handled via the shared upcoming helper).
        """
        launches = [
            {
                "id": f"up-{i}",
                # all future dates
                "net": f"2050-11-{10 + i:02d}T10:00:00Z"
            }
            for i in range(6)
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": launches}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_upcoming_launches(limit=3)

        # Now we expect exactly 'limit' results
        self.assertEqual(len(result), 3)
        # And they should be the ones after the hero candidate
        self.assertEqual([r["id"] for r in result], ["up-1", "up-2", "up-3"])

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_recent_and_completed(self, mock_get):
        """Test fetching recent and completed launches."""
        launches = [
            {
                "id": f"launch-{i}",
                "net": f"2025-11-{15 - i:02d}T10:00:00Z",
                "status": {"name": "Success"}
            }
            for i in range(10)
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": launches}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_recent_and_completed(
            recent_limit=3, completed_limit=2
        )

        self.assertIn("recent", result)
        self.assertIn("completed", result)

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_launch_by_id(self, mock_get):
        """Test fetching a specific launch by ID."""
        mock_response = MagicMock()
        # minimal launch; no mission → get_mission_patches() returns []
        mock_response.json.return_value = {"id": "specific-123"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_launch_by_id("specific-123")

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "specific-123")
        # mission_patches should at least exist as a list
        self.assertIn("mission_patches", result)
        self.assertIsInstance(result["mission_patches"], list)

    # ---------- NEW / UPDATED TESTS FOR get_mission_patches ----------

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_mission_patches_empty_results(self, mock_get):
        """If API returns no patches, we should get an empty list."""
        launch = {
            "id": "launch-1",
            "mission": {
                "name": "Raise and Shine (RAISE-4)",
                "agencies": []
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_mission_patches(launch)

        self.assertEqual(result, [])

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_mission_patches_picks_best_patch(self, mock_get):
        """
        When the API returns multiple candidate patches, make sure we
        pick the one that best matches the mission (name + agency).
        """
        launch = {
            "id": "launch-2",
            "mission": {
                "name": "Starlink Group 11-25",
                "agencies": [{"id": 121}]
            }
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 999,
                    "name": "Totally Unrelated Patch",
                    "priority": 5,
                    "image_url": "https://example.com/unrelated.png",
                    "agency": {"id": 999, "name": "Other"}
                },
                {
                    "id": 7,
                    "name": "Space X Starlink Mission Patch",
                    "priority": 10,
                    "image_url": "https://example.com/starlink.png",
                    "agency": {"id": 121, "name": "SpaceX"}
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_mission_patches(launch)

        # We return a single best patch in a list
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 7)
        self.assertIn("starlink", result[0]["name"].lower())

    def test_extract_youtube_id(self):
        """Test YouTube ID extraction."""
        url = "https://www.youtube.com/watch?v=abc123defgh"
        result = spacedev_api.extract_youtube_id(url)
        self.assertEqual(result, "abc123defgh")

    def test_get_best_video_url(self):
        """Test video URL extraction."""
        launch = {
            "vidURLs": [
                {"url": "https://example.com/1", "type": {"name": "Other"}},
                {"url": "https://example.com/2", "type": {"name": "Official Webcast"}}
            ]
        }
        result = spacedev_api.get_best_video_url(launch)
        self.assertEqual(result, "https://example.com/2")

    @patch('launches.api.spacedev_api.get_next_launch')
    def test_get_full_launch_data(self, mock_next):
        """Test full launch data retrieval."""
        mock_next.return_value = {"id": "test", "vidURLs": []}
        result = spacedev_api.get_full_launch_data()
        self.assertIn("video_url", result)

    @patch('launches.api.spacedev_api.get_recent_and_completed')
    def test_get_recent_launches(self, mock_split):
        """Test recent launches helper."""
        mock_split.return_value = {"recent": [{"id": "1"}], "completed": []}
        result = spacedev_api.get_recent_launches(5)
        self.assertEqual(len(result), 1)

    @patch('launches.api.spacedev_api.get_recent_and_completed')
    def test_get_completed_launches(self, mock_split):
        """Test completed launches helper."""
        mock_split.return_value = {"recent": [], "completed": [{"id": "1"}]}
        result = spacedev_api.get_completed_launches(5)
        self.assertEqual(len(result), 1)


class LaunchViewsTests(TestCase):
    """Test suite for launch views."""

    @patch('launches.views.get_upcoming_launches')
    @patch('launches.views.get_recent_launches')
    @patch('launches.views.get_completed_launches')
    @patch('launches.views.spacedev_hero')
    def test_show_launches_view(self, mock_hero, mock_completed,
                                mock_recent, mock_upcoming):
        """Test show_launches view."""
        mock_hero.return_value = {
            "mission_name": "Test",
            "launch_id": "test-123"
        }
        mock_upcoming.return_value = [{"id": "1", "name": "Test"}]
        mock_recent.return_value = []
        mock_completed.return_value = []

        response = self.client.get(reverse('launches:launch'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('hero', response.context)

    @patch('launches.views.get_launch_by_id')
    def test_full_launch_detail_success(self, mock_get_launch):
        """Test full_launch_detail view."""
        mock_get_launch.return_value = {"id": "test-123", "name": "Test"}

        response = self.client.get(
            reverse('launches:full_launch', args=['test-123'])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('launch', response.context)
