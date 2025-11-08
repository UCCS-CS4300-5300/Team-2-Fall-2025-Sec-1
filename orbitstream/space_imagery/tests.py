"""
Test cases for the space_imagery app
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch, Mock
import requests

from space_imagery import views, utils
from space_imagery.utils import NasaApiError


class UtilsTestCase(TestCase):
    """Test cases for utils.py"""
    
    @override_settings(NASA_API_KEY='test_api_key_123')
    @patch('space_imagery.utils.SESSION.get')
    def test_get_success(self, mock_get):
        """Test successful API request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "collection": {
                "items": [
                    {"data": [{"title": "Test Image"}]}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        result = utils.get("search", {"q": "mars"})
        
        self.assertEqual(result["collection"]["items"][0]["data"][0]["title"], "Test Image")
        mock_get.assert_called_once()
    
    @override_settings(NASA_API_KEY='test_api_key_123')
    @patch('space_imagery.utils.SESSION.get')
    def test_get_with_empty_params(self, mock_get):
        """Test API request with no params"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response
        
        result = utils.get("search")
        
        mock_get.assert_called_once()
    
    @patch('space_imagery.utils.SESSION.get')
    def test_get_404_error(self, mock_get):
        """Test API request with 404 error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_get.return_value = mock_response
        
        with self.assertRaises(NasaApiError) as context:
            utils.get("invalid/path")
        
        self.assertIn("404", str(context.exception))
    
    @patch('space_imagery.utils.SESSION.get')
    def test_get_500_error(self, mock_get):
        """Test API request with server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Invalid JSON")
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        with self.assertRaises(NasaApiError) as context:
            utils.get("search")
        
        self.assertIn("500", str(context.exception))
        self.assertIn("Internal Server Error", str(context.exception))
    
    @patch('space_imagery.utils.SESSION.get')
    def test_get_timeout(self, mock_get):
        """Test API request timeout"""
        mock_get.side_effect = requests.Timeout("Request timed out")
        
        with self.assertRaises(requests.Timeout):
            utils.get("search", timeout=1)
    
    def test_add_key_with_params(self):
        """Test _add_key helper function with existing params"""
        with override_settings(NASA_API_KEY='my_key'):
            params = {"q": "mars", "media_type": "image"}
            result = utils._add_key(params)
            
            self.assertEqual(result["api_key"], "my_key")
            self.assertEqual(result["q"], "mars")
            self.assertEqual(result["media_type"], "image")
    
    def test_add_key_with_none(self):
        """Test _add_key helper function with None params"""
        with override_settings(NASA_API_KEY='my_key'):
            result = utils._add_key(None)
            
            self.assertEqual(result["api_key"], "my_key")
            self.assertEqual(len(result), 1)


class GalleryViewTestCase(TestCase):
    """Test cases for gallery view"""
    
    @patch('space_imagery.utils.get')
    def test_gallery_with_search_query(self, mock_get):
        """Test gallery view with a search query"""
        mock_get.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Mars Rover"}],
                        "links": [{"href": "http://example.com/image.jpg"}]
                    }
                ]
            }
        }
        
        response = self.client.get('/gallery/', {'q': 'mars', 'type': 'image'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('items', response.context)
        self.assertEqual(len(response.context['items']), 1)
        self.assertEqual(response.context['q'], 'mars')
        self.assertEqual(response.context['media_type'], 'image')
        
        # Verify API was called with correct params
        mock_get.assert_called_once_with(
            "search", 
            {"q": "mars", "media_type": "image", "page": "1"}
        )
    
    @patch('space_imagery.utils.get')
    def test_gallery_without_search_query(self, mock_get):
        """Test gallery view without search query (empty state)"""
        response = self.client.get('/gallery/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('items', response.context)
        self.assertEqual(len(response.context['items']), 0)
        self.assertEqual(response.context['q'], '')
        
        # API should not be called when query is empty
        mock_get.assert_not_called()
    
    @patch('space_imagery.utils.get')
    def test_gallery_with_video_type(self, mock_get):
        """Test gallery view with video media type"""
        mock_get.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "ISS Video"}],
                        "links": [{"href": "http://example.com/video.mp4"}]
                    }
                ]
            }
        }
        
        response = self.client.get('/gallery/', {'q': 'ISS', 'type': 'video'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['media_type'], 'video')
        
        # Verify API was called with video type
        call_args = mock_get.call_args[0][1]
        self.assertEqual(call_args['media_type'], 'video')
    
    @patch('space_imagery.utils.get')
    def test_gallery_with_pagination(self, mock_get):
        """Test gallery view with page parameter"""
        mock_get.return_value = {
            "collection": {
                "items": []
            }
        }
        
        response = self.client.get('/gallery/', {'q': 'moon', 'page': '3'})
        
        self.assertEqual(response.context['page'], '3')
        
        # Verify API was called with correct page
        call_args = mock_get.call_args[0][1]
        self.assertEqual(call_args['page'], '3')
    
    @patch('space_imagery.utils.get')
    def test_gallery_default_values(self, mock_get):
        """Test gallery view uses default values correctly"""
        mock_get.return_value = {
            "collection": {
                "items": []
            }
        }
        
        response = self.client.get('/gallery/', {'q': 'space'})
        
        # Should use default values for type and page
        self.assertEqual(response.context['media_type'], 'image')
        self.assertEqual(response.context['page'], '1')
    
    @patch('space_imagery.utils.get')
    def test_gallery_api_error_handling(self, mock_get):
        """Test gallery view handles API errors"""
        mock_get.side_effect = NasaApiError("API Error")
        
        # The view should handle this - if not, this will raise an error
        # You may want to add try/except in your view to handle this gracefully
        with self.assertRaises(NasaApiError):
            self.client.get('/gallery/', {'q': 'mars'})
    
    @patch('space_imagery.utils.get')
    def test_gallery_empty_collection(self, mock_get):
        """Test gallery view with empty collection from API"""
        mock_get.return_value = {
            "collection": {
                "items": []
            }
        }
        
        response = self.client.get('/gallery/', {'q': 'nonexistent'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['items']), 0)
    
    @patch('space_imagery.utils.get')
    def test_gallery_malformed_api_response(self, mock_get):
        """Test gallery view with malformed API response"""
        mock_get.return_value = {}
        
        response = self.client.get('/gallery/', {'q': 'test'})
        
        # Should handle missing 'collection' key gracefully
        self.assertEqual(len(response.context['items']), 0)


class FullMediaViewTestCase(TestCase):
    """Test cases for full_media view"""
    
    def test_full_media_no_nasa_id(self):
        """Test full_media view without nasa_id parameter"""
        response = self.client.get(reverse('space_imagery:full_media'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertEqual(response.context['error'], 'No media ID provided')
    
    @patch('space_imagery.utils.get')
    def test_full_media_not_found(self, mock_get):
        """Test full_media view when media is not found"""
        mock_get.return_value = {"collection": {"items": []}}
        
        response = self.client.get(
            reverse('space_imagery:full_media'),
            {'nasa_id': 'nonexistent'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertEqual(response.context['error'], 'Media not found')
    
    @patch('requests.get')
    @patch('space_imagery.utils.get')
    def test_full_media_image_success(self, mock_utils_get, mock_requests_get):
        """Test full_media view with successful image retrieval"""
        # Mock utils.get for search
        mock_utils_get.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{
                            "title": "Mars Surface",
                            "description": "A beautiful view of Mars",
                            "nasa_id": "PIA12345",
                            "media_type": "image",
                            "date_created": "2024-01-15T00:00:00Z",
                            "center": "JPL",
                            "keywords": ["mars", "surface", "rover"]
                        }],
                        "href": "http://example.com/assets/PIA12345",
                        "links": [{"href": "http://example.com/thumb.jpg"}]
                    }
                ]
            }
        }
        
        # Mock requests.get for asset manifest
        mock_asset_response = Mock()
        mock_asset_response.status_code = 200
        mock_asset_response.json.return_value = [
            "http://example.com/PIA12345~small.jpg",
            "http://example.com/PIA12345~large.jpg",
            "http://example.com/PIA12345~orig.jpg"
        ]
        mock_requests_get.return_value = mock_asset_response
        
        response = self.client.get(
            reverse('space_imagery:full_media'),
            {'nasa_id': 'PIA12345'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('item', response.context)
        self.assertIn('media_url', response.context)
        self.assertEqual(response.context['item']['title'], 'Mars Surface')
        self.assertEqual(response.context['media_type'], 'image')
        # Should get the large version
        self.assertIn('~large', response.context['media_url'])
    
    @patch('requests.get')
    @patch('space_imagery.utils.get')
    def test_full_media_video_success(self, mock_utils_get, mock_requests_get):
        """Test full_media view with successful video retrieval"""
        mock_utils_get.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{
                            "title": "ISS Spacewalk",
                            "description": "Astronaut spacewalk footage",
                            "nasa_id": "VID67890",
                            "media_type": "video"
                        }],
                        "href": "http://example.com/assets/VID67890",
                        "links": [{"href": "http://example.com/thumb.jpg"}]
                    }
                ]
            }
        }
        
        # Mock requests.get for asset manifest with video
        mock_asset_response = Mock()
        mock_asset_response.status_code = 200
        mock_asset_response.json.return_value = [
            "http://example.com/VID67890.mp4",
            "http://example.com/VID67890.srt"
        ]
        mock_requests_get.return_value = mock_asset_response
        
        response = self.client.get(
            reverse('space_imagery:full_media'),
            {'nasa_id': 'VID67890'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['media_type'], 'video')
        self.assertIn('.mp4', response.context['media_url'])
    
    @patch('requests.get')
    @patch('space_imagery.utils.get')
    def test_full_media_asset_fetch_failure(self, mock_utils_get, mock_requests_get):
        """Test full_media view when asset fetch fails"""
        mock_utils_get.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{
                            "title": "Test Image",
                            "nasa_id": "TEST123",
                            "media_type": "image"
                        }],
                        "href": "http://example.com/assets/TEST123",
                        "links": [{"href": "http://example.com/fallback.jpg"}]
                    }
                ]
            }
        }
        
        # Mock failed asset fetch
        mock_requests_get.side_effect = Exception("Connection error")
        
        response = self.client.get(
            reverse('space_imagery:full_media'),
            {'nasa_id': 'TEST123'}
        )
        
        self.assertEqual(response.status_code, 200)
        # Should fallback to links
        self.assertEqual(response.context['media_url'], 'http://example.com/fallback.jpg')
    
    @patch('requests.get')
    @patch('space_imagery.utils.get')
    def test_full_media_no_href(self, mock_utils_get, mock_requests_get):
        """Test full_media view when item has no href"""
        mock_utils_get.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{
                            "title": "Test Image",
                            "nasa_id": "TEST456",
                            "media_type": "image"
                        }],
                        "links": [{"href": "http://example.com/direct.jpg"}]
                    }
                ]
            }
        }
        
        response = self.client.get(
            reverse('space_imagery:full_media'),
            {'nasa_id': 'TEST456'}
        )
        
        self.assertEqual(response.status_code, 200)
        # Should use direct link
        self.assertEqual(response.context['media_url'], 'http://example.com/direct.jpg')
        # requests.get should not be called since there's no href
        mock_requests_get.assert_not_called()
    
    @patch('space_imagery.utils.get')
    def test_full_media_no_media_url(self, mock_utils_get):
        """Test full_media view when no media URL can be found"""
        mock_utils_get.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{
                            "title": "Test Image",
                            "nasa_id": "TEST789",
                            "media_type": "image"
                        }]
                    }
                ]
            }
        }
        
        response = self.client.get(
            reverse('space_imagery:full_media'),
            {'nasa_id': 'TEST789'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['media_url'])


class URLTestCase(TestCase):
    """Test cases for urls.py"""
    
    def test_gallery_url_resolves(self):
        """Test that gallery URL resolves correctly"""
        url = reverse('space_imagery:gallery')
        self.assertEqual(url, '/gallery/')  # Adjust based on your URL config
    
    def test_full_media_url_resolves(self):
        """Test that full_media URL resolves correctly"""
        url = reverse('space_imagery:full_media')
        self.assertEqual(url, '/gallery/media/')  # Adjust based on your URL config
    
    @patch('space_imagery.utils.get')
    def test_gallery_url_accessible(self, mock_get):
        """Test that gallery URL is accessible"""
        mock_get.return_value = {"collection": {"items": []}}
        
        response = self.client.get(reverse('space_imagery:gallery'))
        self.assertEqual(response.status_code, 200)
    
    @patch('space_imagery.utils.get')
    def test_gallery_url_with_query_params(self, mock_get):
        """Test gallery URL with query parameters"""
        mock_get.return_value = {"collection": {"items": []}}
        
        response = self.client.get(
            reverse('space_imagery:gallery') + '?q=mars&type=video&page=2'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_full_media_url_accessible(self):
        """Test that full_media URL is accessible"""
        response = self.client.get(reverse('space_imagery:full_media'))
        self.assertEqual(response.status_code, 200)


class IntegrationTestCase(TestCase):
    """Integration tests combining multiple components"""
    
    @patch('space_imagery.utils.SESSION.get')
    def test_full_search_flow(self, mock_get):
        """Test complete search flow from URL to response"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Moon Landing"}],
                        "links": [{"href": "http://example.com/moon.jpg"}]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        # Make request through Django test client
        response = self.client.get(
            reverse('space_imagery:gallery'),
            {'q': 'moon', 'type': 'image'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'moon')  # Query should be in context
        
        # Verify the mock was called
        self.assertTrue(mock_get.called)