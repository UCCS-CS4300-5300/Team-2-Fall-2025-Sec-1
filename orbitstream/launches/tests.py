"""
Tests for the launches app.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
import requests

from launches.api import spacedev_api


class SpaceDevAPITests(TestCase):
    """Test suite for SpaceDevs API functions."""

    def setUp(self):
        """Clear cache before each test."""
        spacedev_api._cache.clear()

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_next_launch_success(self, mock_get):
        """Test successful fetch of next launch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{
                "id": "test-123",
                "name": "Falcon 9 | Starlink",
                "net": "2025-11-20T10:30:00Z"
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
                "net": "2025-11-20T10:00:00Z",
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
        """Test fetching multiple upcoming launches."""
        launches = [
            {"id": f"up-{i}", "net": f"2025-11-{20+i}T10:00:00Z"}
            for i in range(5)
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": launches}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_upcoming_launches(limit=3)

        self.assertEqual(len(result), 3)

    @patch('launches.api.spacedev_api.requests.get')
    def test_get_recent_and_completed(self, mock_get):
        """Test fetching recent and completed launches."""
        launches = [
            {"id": f"launch-{i}", "net": f"2025-11-{15-i}T10:00:00Z",
             "status": {"name": "Success"}}
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
        mock_response.json.return_value = {"id": "specific-123"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = spacedev_api.get_launch_by_id("specific-123")

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "specific-123")


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