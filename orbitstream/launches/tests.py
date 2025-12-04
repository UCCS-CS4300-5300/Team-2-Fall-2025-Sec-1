"""
Tests for the launches app.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
import datetime

# Make sure this import matches your folder structure
from launches.api import spacedev_api

class SpaceDevAPITests(TestCase):
    """Test suite for SpaceDevs API functions."""

    def setUp(self):
        """Clear cache before each test."""
        # Ensure _cache exists in your api module, otherwise this line might error
        if hasattr(spacedev_api, '_cache'):
            spacedev_api._cache.clear()

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_next_launch_success(self, mock_get):
        """Test successful fetch of next launch."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200  # <--- CRITICAL FIX: Ensure status is 200
        mock_response.json.return_value = {
            "results": [{
                "id": "test-123",
                "name": "Falcon 9 | Starlink",
                # Future date ensures it's picked up
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
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_next_launch()

        self.assertIsNone(result)

    @patch('launches.api.spacedev_api.requests.get')
    def test_spacedev_hero_success(self, mock_get):
        """Test hero data extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{
                "id": "hero-123",
                "name": "Mission Name",
                "net": "2050-11-20T10:00:00Z",
                "image": "https://example.com/img.jpg",
                "rocket": {"configuration": {"full_name": "Falcon 9"}},
                "pad": {"name": "Launch Pad", "location": {"name": "Location"}},
                "vidURLs": [{"url": "http://youtube.com/watch?v=123", "type": {"name": "Official Webcast"}}]
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.spacedev_hero()

        self.assertIsNotNone(result)
        self.assertEqual(result["mission_name"], "Mission Name")
        self.assertEqual(result["launch_id"], "hero-123")
        self.assertEqual(result["youtube_id"], "123")

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_upcoming_launches(self, mock_get):
        """
        Test fetching multiple upcoming launches.
        Should skip the first result (the hero) and return the rest.
        """
        # Create 6 future launches
        launches = [
            {
                "id": f"up-{i}",
                "net": f"2050-11-{10 + i:02d}T10:00:00Z"
            }
            for i in range(6)
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": launches}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_upcoming_launches(limit=3)

        # Expect 3 results
        self.assertEqual(len(result), 3)
        # Should start from index 1 ("up-1") because index 0 is the hero
        self.assertEqual([r["id"] for r in result], ["up-1", "up-2", "up-3"])

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_recent_and_completed(self, mock_get):
        """Test fetching recent and completed launches."""
        # Create a mix of launches
        launches = [
            {
                "id": f"launch-{i}",
                "net": f"2024-01-{15 - i:02d}T10:00:00Z",
                "status": {"name": "Success"}
            }
            for i in range(10)
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": launches}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_recent_and_completed(
            recent_limit=3, completed_limit=2
        )

        self.assertIn("recent", result)
        self.assertIn("completed", result)
        self.assertEqual(len(result["recent"]), 3)

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_launch_by_id(self, mock_get):
        """
        Test fetching a specific launch by ID.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "specific-123"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_launch_by_id("specific-123")

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "specific-123")

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_mission_patches(self, mock_get):
        """
        Test fetching mission patches.
        """
        # 1. Setup the mock response from the API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"name": "Raise and Shine Patch", "agency": {"id": 1}}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # 2. Input data
        launch_data = {
            "mission": {
                "name": "Raise and Shine",
                "agencies": [{"id": 1}]
            }
        }

        # 3. Call the function
        result = spacedev_api.get_mission_patches(launch_data)

        # 4. Verify results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Raise and Shine Patch")

        # 5. Verify parameters
        args, kwargs = mock_get.call_args
        params = kwargs['params']
        self.assertIn("name__contains", params)
        self.assertEqual(params["name__contains"], "Raise and Shine")
        self.assertEqual(params["limit"], 100)

    def test_extract_youtube_id(self):
        """Test YouTube ID extraction."""
        url = "https://www.youtube.com/watch?v=abc123defgh"
        result = spacedev_api.extract_youtube_id(url)
        self.assertEqual(result, "abc123defgh")

        url_short = "https://youtu.be/xyz98765432"
        result_short = spacedev_api.extract_youtube_id(url_short)
        self.assertEqual(result_short, "xyz98765432")

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


class LaunchViewsTests(TestCase):
    """Test suite for launch views."""

    @patch('launches.views.get_upcoming_launches')
    @patch('launches.views.get_recent_launches')
    @patch('launches.views.get_completed_launches')
    @patch('launches.views.spacedev_hero')
    def test_show_launches_view(self, mock_hero, mock_completed, 
                                mock_recent, mock_upcoming):
        """
        Test show_launches_view.
        
        NOTE: Arguments must match decorator order (Top-Down).
        1. @patch(...upcoming)  -> mock_upcoming
        2. @patch(...recent)    -> mock_recent
        3. @patch(...completed) -> mock_completed
        4. @patch(...hero)      -> mock_hero
        """
        # Set return values for the correct mocks
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
        mock_get_launch.return_value = {
            "id": "test-123", 
            "name": "Test",
            "pad": {"latitude": 28.5, "longitude": -80.5}
        }

        response = self.client.get(
            reverse('launches:full_launch', args=['test-123'])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('launch', response.context)
        self.assertEqual(response.context['pad_lat'], 28.5)