"""
Test cases for the learn_page app
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch, Mock
import json
import openai

from learn_page.views import validate_space_topic, PREDEFINED_TOPICS


class ValidateSpaceTopicTestCase(TestCase):
    """Test cases for validate_space_topic function"""

    @override_settings(OPENAI_API_KEY=None)
    def test_validation_skipped_without_api_key(self):
        """Test that validation is skipped if no API key is configured"""
        is_valid, message = validate_space_topic("anything")
        self.assertTrue(is_valid)
        self.assertIsNone(message)

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_valid_space_topic(self, mock_openai):
        """Test validation of a valid space topic"""
        # Mock OpenAI client and response
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "YES"
        mock_client.chat.completions.create.return_value = mock_response

        is_valid, message = validate_space_topic("satellites")

        self.assertTrue(is_valid)
        self.assertIsNone(message)
        mock_client.chat.completions.create.assert_called_once()

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_invalid_non_space_topic(self, mock_openai):
        """Test validation of a non-space topic"""
        # Mock OpenAI client and response
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "NO"
        mock_client.chat.completions.create.return_value = mock_response

        is_valid, message = validate_space_topic("cooking recipes")

        self.assertFalse(is_valid)
        self.assertIsNotNone(message)
        self.assertIn("doesn't appear to be related to space", message)
        self.assertIn("cooking recipes", message)

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_validation_error_allows_topic(self, mock_openai):
        """Test that API errors allow the topic through"""
        # Mock OpenAI to raise an exception
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        is_valid, message = validate_space_topic("satellites")

        # Should allow topic through on error
        self.assertTrue(is_valid)
        self.assertIsNone(message)


class LearnPageViewTestCase(TestCase):
    """Test cases for learn_page view"""

    def test_learn_page_loads_successfully(self):
        """Test that the learn page loads with 200 status"""
        response = self.client.get(reverse('learn_page:learn_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'learn_page/learn_page.html')

    def test_learn_page_contains_predefined_topics(self):
        """Test that predefined topics are passed to template"""
        response = self.client.get(reverse('learn_page:learn_page'))

        self.assertIn('topics', response.context)
        topics = response.context['topics']
        self.assertEqual(len(topics), 8)

        # Check that topics match PREDEFINED_TOPICS
        self.assertEqual(topics, PREDEFINED_TOPICS)

    def test_learn_page_topics_structure(self):
        """Test that topics have required structure"""
        response = self.client.get(reverse('learn_page:learn_page'))
        topics = response.context['topics']

        # Verify each topic has required fields
        for topic in topics:
            self.assertIn('id', topic)
            self.assertIn('title', topic)
            self.assertIn('icon', topic)
            self.assertIn('description', topic)

    def test_learn_page_specific_topics_exist(self):
        """Test that specific expected topics exist"""
        response = self.client.get(reverse('learn_page:learn_page'))
        topics = response.context['topics']

        topic_titles = [t['title'] for t in topics]
        self.assertIn('Satellites & Their Functions', topic_titles)
        self.assertIn('Space Debris Tracking', topic_titles)
        self.assertIn('Black Holes', topic_titles)
        self.assertIn('International Space Station', topic_titles)


class GenerateSummaryViewTestCase(TestCase):
    """Test cases for generate_summary view"""

    def test_requires_post_method(self):
        """Test that only POST requests are allowed"""
        response = self.client.get(reverse('learn_page:generate_summary'))
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_empty_topic_returns_error(self):
        """Test that empty topic returns 400 error"""
        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": ""}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('provide a topic', data['error'])

    def test_missing_topic_returns_error(self):
        """Test that missing topic key returns 400 error"""
        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_whitespace_only_topic_returns_error(self):
        """Test that whitespace-only topic is treated as empty"""
        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "   "}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(OPENAI_API_KEY=None)
    def test_missing_api_key_returns_error(self):
        """Test that missing API key returns 503 error"""
        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "satellites"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('not configured', data['error'])
        self.assertTrue(data.get('fallback'))

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_non_space_topic_rejected(self, mock_openai):
        """Test that non-space topics are rejected"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock validation response (NO)
        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "NO"
        mock_client.chat.completions.create.return_value = mock_validation

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "cooking"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertTrue(data.get('fallback'))
        self.assertIn("doesn't appear to be related to space", data['error'])

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_successful_summary_generation(self, mock_openai):
        """Test successful summary generation"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock validation response (YES)
        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "YES"

        # Mock summary response
        mock_summary = Mock()
        mock_summary.choices = [Mock()]
        mock_summary.choices[0].message.content = (
            "Satellites are artificial objects placed in orbit around Earth. "
            "They serve various purposes including communication, navigation, and observation. "
            "Modern satellites use advanced technology to monitor weather, enable GPS, and facilitate global communications.\n\n"
            "**Related Topics:** GPS, Space Stations, Orbital Mechanics"
        )

        # Set up the mock to return different responses for validation and summary
        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            mock_summary
        ]

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "satellites"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['topic'], 'satellites')
        self.assertIn('Satellites are artificial', data['summary'])
        self.assertIn('GPS', data['keywords'])
        self.assertIn('Orbital Mechanics', data['keywords'])

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_summary_without_keywords(self, mock_openai):
        """Test summary generation when keywords are not present"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock validation response (YES)
        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "YES"

        # Mock summary response without keywords section
        mock_summary = Mock()
        mock_summary.choices = [Mock()]
        mock_summary.choices[0].message.content = (
            "Satellites are artificial objects in orbit around Earth."
        )

        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            mock_summary
        ]

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "satellites"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['keywords'], '')

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_openai_api_error_handling(self, mock_openai):
        """Test handling of OpenAI API errors"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Validation succeeds
        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "YES"

        # Summary generation raises APIError (APIError requires message and request params)
        api_error = openai.APIError(message="API Error", request=Mock(), body=None)
        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            api_error
        ]

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "satellites"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertIn('error', data)
        self.assertTrue(data.get('fallback'))

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_general_exception_handling(self, mock_openai):
        """Test handling of general exceptions"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Validation succeeds
        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "YES"

        # Summary generation raises general exception
        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            Exception("Unexpected error")
        ]

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "satellites"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertTrue(data.get('fallback'))


class URLTestCase(TestCase):
    """Test cases for URLs"""

    def test_learn_page_url_resolves(self):
        """Test that learn_page URL resolves correctly"""
        url = reverse('learn_page:learn_page')
        # Adjust based on your actual URL pattern
        self.assertTrue(url.endswith('/learn_page/') or url.endswith('/learn_page'))

    def test_generate_summary_url_resolves(self):
        """Test that generate_summary URL resolves correctly"""
        url = reverse('learn_page:generate_summary')
        # Adjust based on your actual URL pattern
        self.assertTrue('summary' in url or 'generate' in url)

    def test_learn_page_url_accessible(self):
        """Test that learn_page URL is accessible"""
        response = self.client.get(reverse('learn_page:learn_page'))
        self.assertEqual(response.status_code, 200)

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_generate_summary_url_accessible(self, mock_openai):
        """Test that generate_summary URL is accessible with POST"""
        # Mock OpenAI responses
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "YES"

        mock_summary = Mock()
        mock_summary.choices = [Mock()]
        mock_summary.choices[0].message.content = "Test summary\n\n**Related Topics:** test"

        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            mock_summary
        ]

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "test"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)


class IntegrationTestCase(TestCase):
    """Integration tests combining multiple components"""

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_complete_user_flow(self, mock_openai):
        """Test complete user flow from page load to summary generation"""
        # Step 1: Load the learn page
        response = self.client.get(reverse('learn_page:learn_page'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('topics', response.context)

        # Step 2: Generate a summary for a valid topic
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "YES"

        mock_summary = Mock()
        mock_summary.choices = [Mock()]
        mock_summary.choices[0].message.content = (
            "Black holes are regions of spacetime with extreme gravity. "
            "Nothing can escape from within their event horizon, not even light. "
            "They form when massive stars collapse at the end of their lives.\n\n"
            "**Related Topics:** Event Horizon, Singularity, Hawking Radiation"
        )

        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            mock_summary
        ]

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "black holes"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('black holes', data['topic'].lower())
        self.assertIn('Event Horizon', data['keywords'])

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_predefined_topic_flow(self, mock_openai):
        """Test flow using a predefined topic"""
        # Get a predefined topic
        topic_title = PREDEFINED_TOPICS[0]['title']

        # Mock OpenAI responses
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "YES"

        mock_summary = Mock()
        mock_summary.choices = [Mock()]
        mock_summary.choices[0].message.content = f"Summary about {topic_title}\n\n**Related Topics:** topic1, topic2"

        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            mock_summary
        ]

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": topic_title}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['topic'], topic_title)

    @override_settings(OPENAI_API_KEY='test_api_key_123')
    @patch('learn_page.views.openai.OpenAI')
    def test_invalid_topic_rejection_flow(self, mock_openai):
        """Test complete flow for invalid topic rejection"""
        # Mock OpenAI to reject non-space topic
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        mock_validation.choices[0].message.content = "NO"
        mock_client.chat.completions.create.return_value = mock_validation

        response = self.client.post(
            reverse('learn_page:generate_summary'),
            data=json.dumps({"topic": "baking cookies"}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('space', data['error'].lower())