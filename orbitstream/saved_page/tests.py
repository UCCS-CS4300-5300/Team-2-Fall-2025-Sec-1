import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, MagicMock
from io import BytesIO
from saved_page.models import (
    SavedSatellite,
    SavedGalleryItem,
    SavedLaunch,
    SavedLearnTopic,
    SavedNewsArticle,
)


class SavedPageViewsTestCase(TestCase):
    """Test cases for saved_page views"""

    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_saved_page_requires_login(self):
        """Test that saved page requires authentication"""
        self.client.logout()
        response = self.client.get(reverse('saved_page:saved_page'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_saved_page_loads(self):
        """Test that saved page loads successfully for authenticated user"""
        response = self.client.get(reverse('saved_page:saved_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'saved_page/saved_page.html')

    # Satellite Tests
    def test_toggle_save_satellite_create(self):
        """Test saving a new satellite"""
        data = {
            'satellite_id': 12345,
            'name': 'Test Satellite',
            'altitude': 400.5,
            'azimuth': 180.0,
            'elevation': 45.0,
            'latitude': 40.7128,
            'longitude': -74.0060,
        }
        response = self.client.post(
            reverse('saved_page:toggle_save_satellite'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['saved'])
        self.assertEqual(SavedSatellite.objects.filter(user=self.user).count(), 1)

    def test_toggle_save_satellite_delete(self):
        """Test unsaving an existing satellite"""
        SavedSatellite.objects.create(
            user=self.user,
            satellite_id=12345,
            name='Test Satellite'
        )
        data = {'satellite_id': 12345, 'name': 'Test Satellite'}
        response = self.client.post(
            reverse('saved_page:toggle_save_satellite'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result['saved'])
        self.assertEqual(SavedSatellite.objects.filter(user=self.user).count(), 0)

    def test_check_saved_satellite(self):
        """Test checking if a satellite is saved"""
        SavedSatellite.objects.create(
            user=self.user,
            satellite_id=12345,
            name='Test Satellite'
        )
        response = self.client.get(
            reverse('saved_page:check_saved_satellite'),
            {'satellite_id': '12345'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])

    def test_delete_saved_satellite(self):
        """Test deleting a saved satellite"""
        satellite = SavedSatellite.objects.create(
            user=self.user,
            satellite_id=12345,
            name='Test Satellite'
        )
        response = self.client.post(
            reverse('saved_page:delete_saved_satellite', args=[satellite.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(SavedSatellite.objects.filter(user=self.user).count(), 0)

    # Launch Tests
    def test_toggle_save_launch_create(self):
        """Test saving a new launch"""
        data = {
            'launch_id': 'LAUNCH-001',
            'name': 'Falcon 9',
            'status': 'Go',
            'net': '2024-12-10T12:00:00Z',
            'rocket_name': 'Falcon 9 Block 5',
            'pad_name': 'LC-39A',
            'pad_location': 'Kennedy Space Center',
            'image_url': 'https://example.com/image.jpg',
        }
        response = self.client.post(
            reverse('saved_page:toggle_save_launch'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertEqual(SavedLaunch.objects.filter(user=self.user).count(), 1)

    def test_toggle_save_launch_delete(self):
        """Test unsaving an existing launch"""
        SavedLaunch.objects.create(
            user=self.user,
            launch_id='LAUNCH-001',
            name='Falcon 9'
        )
        data = {'launch_id': 'LAUNCH-001', 'name': 'Falcon 9'}
        response = self.client.post(
            reverse('saved_page:toggle_save_launch'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['saved'])
        self.assertEqual(SavedLaunch.objects.filter(user=self.user).count(), 0)

    # Learn Topic Tests
    def test_toggle_save_learn_create(self):
        """Test saving a new learn topic"""
        data = {
            'topic': 'Orbital Mechanics',
            'summary': 'Study of spacecraft motion',
            'keywords': 'orbit, trajectory, velocity',
        }
        response = self.client.post(
            reverse('saved_page:toggle_save_learn'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertEqual(SavedLearnTopic.objects.filter(user=self.user).count(), 1)

    def test_toggle_save_learn_delete(self):
        """Test unsaving an existing learn topic"""
        SavedLearnTopic.objects.create(
            user=self.user,
            topic='Orbital Mechanics',
            summary='Study of spacecraft motion'
        )
        data = {'topic': 'Orbital Mechanics', 'summary': 'Study of spacecraft motion'}
        response = self.client.post(
            reverse('saved_page:toggle_save_learn'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['saved'])
        self.assertEqual(SavedLearnTopic.objects.filter(user=self.user).count(), 0)

    # News Article Tests
    def test_toggle_save_news_create(self):
        """Test saving a new news article"""
        data = {
            'article_url': 'https://example.com/article',
            'title': 'SpaceX Launch Success',
            'description': 'Falcon 9 successfully launches',
            'image_url': 'https://example.com/image.jpg',
            'source_name': 'Space News',
            'published_at': '2024-12-09T10:00:00Z',
            'content': 'Full article content here',
            'author': 'John Doe',
        }
        response = self.client.post(
            reverse('saved_page:toggle_save_news'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertEqual(SavedNewsArticle.objects.filter(user=self.user).count(), 1)

    def test_toggle_save_news_delete(self):
        """Test unsaving an existing news article"""
        SavedNewsArticle.objects.create(
            user=self.user,
            article_url='https://example.com/article',
            title='SpaceX Launch Success'
        )
        data = {'article_url': 'https://example.com/article', 'title': 'SpaceX Launch Success'}
        response = self.client.post(
            reverse('saved_page:toggle_save_news'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['saved'])
        self.assertEqual(SavedNewsArticle.objects.filter(user=self.user).count(), 0)

    # Gallery Tests with Mocking
    @patch('saved_page.views.download_file_from_url')
    @patch('saved_page.views.create_thumbnail')
    def test_toggle_save_gallery_create(self, mock_thumbnail, mock_download):
        """Test saving a new gallery item with mocked download"""
        # Mock file download
        mock_file = BytesIO(b'fake image data')
        mock_download.return_value = mock_file
        
        # Mock thumbnail creation
        mock_thumb = MagicMock()
        mock_thumb.read.return_value = b'fake thumbnail data'
        mock_thumbnail.return_value = mock_thumb

        data = {
            'nasa_id': 'NASA-001',
            'title': 'Hubble Image',
            'description': 'Beautiful galaxy',
            'media_url': 'https://example.com/image.jpg',
            'thumbnail_url': 'https://example.com/thumb.jpg',
            'media_type': 'image',
        }
        response = self.client.post(
            reverse('saved_page:toggle_save_gallery'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertEqual(SavedGalleryItem.objects.filter(user=self.user).count(), 1)

    def test_toggle_save_gallery_delete(self):
        """Test unsaving an existing gallery item"""
        SavedGalleryItem.objects.create(
            user=self.user,
            nasa_id='NASA-001',
            title='Hubble Image',
            media_url='https://example.com/image.jpg'
        )
        data = {'nasa_id': 'NASA-001', 'title': 'Hubble Image'}
        response = self.client.post(
            reverse('saved_page:toggle_save_gallery'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['saved'])
        self.assertEqual(SavedGalleryItem.objects.filter(user=self.user).count(), 0)

    # Batch Check Tests
    def test_get_saved_ids(self):
        """Test retrieving all saved IDs at once"""
        # Create saved items
        SavedSatellite.objects.create(user=self.user, satellite_id=12345, name='Test')
        SavedLaunch.objects.create(user=self.user, launch_id='LAUNCH-001', name='Test')
        SavedNewsArticle.objects.create(
            user=self.user,
            article_url='https://example.com/article',
            title='Test'
        )

        response = self.client.get(reverse('saved_page:get_saved_ids'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn(12345, data['satellites'])
        self.assertIn('LAUNCH-001', data['launches'])
        self.assertIn('https://example.com/article', data['news'])

    # Error Handling Tests
    def test_toggle_save_satellite_invalid_json(self):
        """Test error handling for invalid JSON"""
        response = self.client.post(
            reverse('saved_page:toggle_save_satellite'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_check_saved_satellite_missing_id(self):
        """Test error handling for missing satellite_id"""
        response = self.client.get(reverse('saved_page:check_saved_satellite'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_delete_saved_satellite_not_found(self):
        """Test deleting non-existent satellite"""
        response = self.client.post(
            reverse('saved_page:delete_saved_satellite', args=[9999])
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_saved_satellite_wrong_user(self):
        """Test that users can only delete their own saved items"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        satellite = SavedSatellite.objects.create(
            user=other_user,
            satellite_id=12345,
            name='Test'
        )
        response = self.client.post(
            reverse('saved_page:delete_saved_satellite', args=[satellite.pk])
        )
        self.assertEqual(response.status_code, 404)

    # View Tests
    def test_view_saved_article(self):
        """Test viewing a saved article"""
        article = SavedNewsArticle.objects.create(
            user=self.user,
            article_url='https://example.com/article',
            title='Test Article',
            full_html='<html>Article content</html>'
        )
        response = self.client.get(
            reverse('saved_page:view_saved_article', args=[article.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'space_news/article.html')
        self.assertTrue(response.context['is_saved_view'])

    def test_view_saved_media(self):
        """Test viewing saved gallery media"""
        media = SavedGalleryItem.objects.create(
            user=self.user,
            nasa_id='NASA-001',
            title='Test Media',
            media_url='https://example.com/image.jpg',
            media_type='image'
        )
        response = self.client.get(
            reverse('saved_page:view_saved_media', args=[media.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'saved_page/saved_media.html')

    def test_serve_gallery_media_no_data(self):
        """Test serving media when no data is stored"""
        media = SavedGalleryItem.objects.create(
            user=self.user,
            nasa_id='NASA-001',
            title='Test Media',
            media_url='https://example.com/image.jpg'
        )
        response = self.client.get(
            reverse('saved_page:serve_gallery_media', args=[media.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_serve_gallery_media_with_data(self):
        """Test serving media from database"""
        media = SavedGalleryItem.objects.create(
            user=self.user,
            nasa_id='NASA-001',
            title='Test Media',
            media_url='https://example.com/image.jpg',
            media_data=b'fake image data',
            media_content_type='image/jpeg',
            media_filename='test.jpg'
        )
        response = self.client.get(
            reverse('saved_page:serve_gallery_media', args=[media.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(response.content, b'fake image data')


class UtilityFunctionsTestCase(TestCase):
    """Test cases for utility functions"""

    @patch('requests.get')
    def test_download_file_from_url_success(self, mock_get):
        """Test successful file download"""
        from saved_page.views import download_file_from_url
        
        # Mock response
        mock_response = MagicMock()
        mock_response.headers.get.return_value = '1024'
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
        mock_get.return_value = mock_response

        result = download_file_from_url('https://example.com/file.jpg')
        self.assertIsNotNone(result)
        result.seek(0)
        self.assertEqual(result.read(), b'chunk1chunk2')

    @patch('requests.get')
    def test_download_file_from_url_timeout(self, mock_get):
        """Test file download timeout handling"""
        from saved_page.views import download_file_from_url
        from requests import Timeout
        
        mock_get.side_effect = Timeout()
        result = download_file_from_url('https://example.com/file.jpg')
        self.assertIsNone(result)

    def test_create_thumbnail(self):
        """Test thumbnail creation from image"""
        from saved_page.views import create_thumbnail
        from PIL import Image
        
        # Create a test image
        img = Image.new('RGB', (800, 600), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)

        # Create thumbnail
        thumbnail = create_thumbnail(img_io, size=(200, 200))
        self.assertIsNotNone(thumbnail)
        
        # Verify thumbnail is smaller
        thumb_img = Image.open(BytesIO(thumbnail.read()))
        self.assertLessEqual(thumb_img.width, 200)
        self.assertLessEqual(thumb_img.height, 200)

    def test_create_thumbnail_rgba_conversion(self):
        """Test thumbnail creation with RGBA image"""
        from saved_page.views import create_thumbnail
        from PIL import Image
        
        # Create RGBA image
        img = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)

        # Create thumbnail (should convert to RGB)
        thumbnail = create_thumbnail(img_io)
        self.assertIsNotNone(thumbnail)