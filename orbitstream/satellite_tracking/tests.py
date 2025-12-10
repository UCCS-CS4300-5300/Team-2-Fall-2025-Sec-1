from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.http import JsonResponse
from unittest.mock import patch, Mock
import json

from satellite_tracking.views import (
    closest_satellite,
    get_closest_satellite_api,
    get_orbital_tracker_satellites,
    get_iss_position
)


class ClosestSatelliteViewTest(TestCase):
    """Tests for the closest_satellite view"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_closest_satellite_authenticated(self):
        """Test that authenticated users can access the page"""
        request = self.factory.get('/satellite-tracking/closest/')
        request.user = self.user
        
        response = closest_satellite(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'is_authenticated', response.content)

    def test_closest_satellite_anonymous(self):
        """Test that anonymous users can access the page"""
        request = self.factory.get('/satellite-tracking/closest/')
        request.user = Mock(is_authenticated=False)
        
        response = closest_satellite(request)
        
        self.assertEqual(response.status_code, 200)


class GetClosestSatelliteAPITest(TestCase):
    """Tests for the get_closest_satellite_api endpoint"""

    def setUp(self):
        self.factory = RequestFactory()
        self.valid_payload = {
            'latitude': 40.7128,
            'longitude': -74.0060,
            'altitude': 0
        }

    @patch('satellite_tracking.views.settings.N2YO_API_KEY', 'test_api_key')
    @patch('satellite_tracking.views.requests.get')
    def test_successful_satellite_fetch(self, mock_get):
        """Test successful satellite data retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'above': [
                {
                    'satname': 'ISS (ZARYA)',
                    'satid': 25544,
                    'satalt': 420.5,
                    'sataz': 45.0,
                    'satel': 30.0,
                    'satra': 123.45,
                    'satdec': 12.34,
                    'satlat': 40.0,
                    'satlng': -75.0
                },
                {
                    'satname': 'HUBBLE',
                    'satid': 20580,
                    'satalt': 540.0,
                    'sataz': 90.0,
                    'satel': 45.0,
                    'satra': 200.0,
                    'satdec': 20.0,
                    'satlat': 41.0,
                    'satlng': -74.0
                }
            ],
            'info': {'category': 'All'}
        }
        mock_get.return_value = mock_response

        request = self.factory.post(
            '/api/closest-satellite/',
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        response = get_closest_satellite_api(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['satellite']['name'], 'ISS (ZARYA)')
        self.assertEqual(data['satellite']['altitude'], 420.5)
        self.assertEqual(data['total_satellites_found'], 2)

    @patch('satellite_tracking.views.settings.N2YO_API_KEY', 'test_api_key')
    @patch('satellite_tracking.views.requests.get')
    def test_no_satellites_found(self, mock_get):
        """Test when no satellites are found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'above': []}
        mock_get.return_value = mock_response

        request = self.factory.post(
            '/api/closest-satellite/',
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        response = get_closest_satellite_api(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 404)
        self.assertIn('error', data)
        self.assertIn('No satellites found', data['error'])

    def test_invalid_latitude(self):
        """Test with invalid latitude values"""
        invalid_payloads = [
            {'latitude': 91, 'longitude': 0},
            {'latitude': -91, 'longitude': 0},
        ]

        for payload in invalid_payloads:
            request = self.factory.post(
                '/api/closest-satellite/',
                data=json.dumps(payload),
                content_type='application/json'
            )

            response = get_closest_satellite_api(request)
            data = json.loads(response.content)

            self.assertEqual(response.status_code, 400)
            self.assertIn('Latitude must be between', data['error'])

    def test_invalid_longitude(self):
        """Test with invalid longitude values"""
        invalid_payloads = [
            {'latitude': 0, 'longitude': 181},
            {'latitude': 0, 'longitude': -181},
        ]

        for payload in invalid_payloads:
            request = self.factory.post(
                '/api/closest-satellite/',
                data=json.dumps(payload),
                content_type='application/json'
            )

            response = get_closest_satellite_api(request)
            data = json.loads(response.content)

            self.assertEqual(response.status_code, 400)
            self.assertIn('Longitude must be between', data['error'])

    def test_invalid_json(self):
        """Test with invalid JSON data"""
        request = self.factory.post(
            '/api/closest-satellite/',
            data='invalid json',
            content_type='application/json'
        )

        response = get_closest_satellite_api(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', data['error'])

    def test_missing_coordinates(self):
        """Test with missing coordinate fields"""
        request = self.factory.post(
            '/api/closest-satellite/',
            data=json.dumps({'latitude': 40.7128}),
            content_type='application/json'
        )

        response = get_closest_satellite_api(request)
        
        self.assertEqual(response.status_code, 400)

    @patch('satellite_tracking.views.settings.N2YO_API_KEY', None)
    def test_missing_api_key(self):
        """Test when API key is not configured"""
        request = self.factory.post(
            '/api/closest-satellite/',
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        response = get_closest_satellite_api(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 500)
        self.assertIn('API key not configured', data['error'])

    @patch('satellite_tracking.views.settings.N2YO_API_KEY', 'test_api_key')
    @patch('satellite_tracking.views.requests.get')
    def test_api_timeout(self, mock_get):
        """Test API timeout handling"""
        mock_get.side_effect = Exception('Connection timeout')

        request = self.factory.post(
            '/api/closest-satellite/',
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )

        response = get_closest_satellite_api(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 500)
        self.assertIn('error', data)


class GetOrbitalTrackerSatellitesTest(TestCase):
    """Tests for the get_orbital_tracker_satellites endpoint"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    @patch('satellite_tracking.views.settings.N2YO_API_KEY', 'test_api_key')
    @patch('satellite_tracking.views.get_iss_position')
    def test_anonymous_user_gets_iss(self, mock_iss):
        """Test that anonymous users get ISS position"""
        mock_iss.return_value = [{
            'id': 25544,
            'name': 'ISS (ZARYA)',
            'latitude': 0,
            'longitude': 0,
            'altitude': 420
        }]

        request = self.factory.get('/api/orbital-tracker-satellites/')
        request.user = Mock(is_authenticated=False)

        response = get_orbital_tracker_satellites(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['satellites']), 1)
        self.assertEqual(data['satellites'][0]['name'], 'ISS (ZARYA)')
        self.assertFalse(data['is_authenticated'])

    @patch('satellite_tracking.views.settings.N2YO_API_KEY', 'test_api_key')
    @patch('satellite_tracking.views.requests.get')
    def test_authenticated_user_with_saved_satellites(self, mock_get):
        """Test authenticated user with saved satellites"""
        # Create saved satellite
        from saved_page.models import SavedSatellite
        SavedSatellite.objects.create(
            user=self.user,
            satellite_id=25544,
            name='ISS (ZARYA)',
            latitude=40.0,
            longitude=-74.0,
            altitude=420
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'info': {'satname': 'ISS (ZARYA)'},
            'positions': [{
                'satlatitude': 41.0,
                'satlongitude': -75.0,
                'sataltitude': 421.0
            }]
        }
        mock_get.return_value = mock_response

        request = self.factory.get('/api/orbital-tracker-satellites/')
        request.user = self.user

        response = get_orbital_tracker_satellites(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['satellites']), 1)
        self.assertTrue(data['is_authenticated'])

    @patch('satellite_tracking.views.settings.N2YO_API_KEY', None)
    def test_missing_api_key_orbital_tracker(self):
        """Test when API key is not configured"""
        request = self.factory.get('/api/orbital-tracker-satellites/')
        request.user = Mock(is_authenticated=False)

        response = get_orbital_tracker_satellites(request)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 500)
        self.assertIn('API key not configured', data['error'])


class GetISSPositionTest(TestCase):
    """Tests for the get_iss_position helper function"""

    @patch('satellite_tracking.views.requests.get')
    def test_successful_iss_fetch(self, mock_get):
        """Test successful ISS position retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'info': {'satname': 'ISS (ZARYA)'},
            'positions': [{
                'satlatitude': 45.0,
                'satlongitude': -80.0,
                'sataltitude': 418.5
            }]
        }
        mock_get.return_value = mock_response

        result = get_iss_position('test_api_key')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 25544)
        self.assertEqual(result[0]['latitude'], 45.0)
        self.assertEqual(result[0]['longitude'], -80.0)

    @patch('satellite_tracking.views.requests.get')
    def test_iss_fetch_failure_returns_fallback(self, mock_get):
        """Test that API failure returns fallback ISS position"""
        mock_get.side_effect = Exception('API Error')

        result = get_iss_position('test_api_key')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 25544)
        self.assertEqual(result[0]['name'], 'ISS (ZARYA)')
        # Fallback position
        self.assertEqual(result[0]['altitude'], 420)
