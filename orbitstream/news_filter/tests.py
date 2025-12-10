from django.test import TestCase
from datetime import datetime, date, timedelta
from news_filters.filters import NewsFilterService


class NewsFilterServiceTest(TestCase):
    """Tests for NewsFilterService"""

    def setUp(self):
        """Set up test data"""
        self.sample_articles = [
            {
                'title': 'NASA Launches New Mars Rover',
                'description': 'NASA successfully launched a new rover to explore Mars',
                'publishedAt': '2024-01-15T10:30:00Z',
                'source': {'name': 'Space.com'}
            },
            {
                'title': 'SpaceX Starship Test Flight',
                'description': 'SpaceX conducted another test of its Starship rocket',
                'publishedAt': '2024-01-20T14:45:00Z',
                'source': {'name': 'The Verge'}
            },
            {
                'title': 'International Space Station Updates',
                'description': 'Astronauts on the ISS conduct important research',
                'publishedAt': '2024-01-10T08:00:00Z',
                'source': {'name': 'NASA News'}
            },
            {
                'title': 'Blue Origin Announces New Mission',
                'description': 'Jeff Bezos company plans lunar lander',
                'publishedAt': '2024-01-25T16:20:00Z',
                'source': {'name': 'TechCrunch'}
            },
            {
                'title': None,  # Test null title
                'description': 'Article with no title',
                'publishedAt': '2024-01-18T12:00:00Z',
                'source': {'name': 'Test Source'}
            }
        ]

    def test_apply_filters_no_filters(self):
        """Test that no filters returns all articles"""
        result = NewsFilterService.apply_filters(self.sample_articles, {})
        self.assertEqual(len(result), 5)
        self.assertEqual(result, self.sample_articles)

    def test_apply_filters_search_query_in_title(self):
        """Test search query filtering in title"""
        filter_params = {'search_query': 'NASA'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 2)
        self.assertIn('NASA', result[0]['title'])
        self.assertIn('NASA', result[1]['source']['name'])

    def test_apply_filters_search_query_in_description(self):
        """Test search query filtering in description"""
        filter_params = {'search_query': 'rocket'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 1)
        self.assertIn('rocket', result[0]['description'].lower())

    def test_apply_filters_search_query_case_insensitive(self):
        """Test that search is case insensitive"""
        filter_params = {'search_query': 'spacex'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'SpaceX Starship Test Flight')

    def test_apply_filters_search_query_with_whitespace(self):
        """Test search query with leading/trailing whitespace"""
        filter_params = {'search_query': '  SpaceX  '}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 1)

    def test_apply_filters_search_query_no_results(self):
        """Test search query that matches nothing"""
        filter_params = {'search_query': 'nonexistent'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 0)

    def test_apply_filters_search_handles_null_title(self):
        """Test search handles articles with null title"""
        filter_params = {'search_query': 'no title'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 1)
        self.assertIn('no title', result[0]['description'].lower())

    def test_apply_filters_date_from(self):
        """Test date_from filter"""
        filter_params = {'date_from': date(2024, 1, 18)}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 3)
        # Should include articles from Jan 18, 20, and 25
        for article in result:
            article_date = datetime.fromisoformat(
                article['publishedAt'].replace('Z', '+00:00')
            ).date()
            self.assertGreaterEqual(article_date, date(2024, 1, 18))

    def test_apply_filters_date_to(self):
        """Test date_to filter"""
        filter_params = {'date_to': date(2024, 1, 15)}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 2)
        # Should include articles from Jan 10 and 15
        for article in result:
            article_date = datetime.fromisoformat(
                article['publishedAt'].replace('Z', '+00:00')
            ).date()
            self.assertLessEqual(article_date, date(2024, 1, 15))

    def test_apply_filters_date_range(self):
        """Test date range with both from and to"""
        filter_params = {
            'date_from': date(2024, 1, 12),
            'date_to': date(2024, 1, 22)
        }
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 3)
        # Should include articles from Jan 15, 18, and 20
        for article in result:
            article_date = datetime.fromisoformat(
                article['publishedAt'].replace('Z', '+00:00')
            ).date()
            self.assertGreaterEqual(article_date, date(2024, 1, 12))
            self.assertLessEqual(article_date, date(2024, 1, 22))

    def test_apply_filters_source_in_title(self):
        """Test source filter matching in title"""
        filter_params = {'source': 'SpaceX'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 1)
        self.assertIn('SpaceX', result[0]['title'])

    def test_apply_filters_source_in_source_name(self):
        """Test source filter matching in source name"""
        filter_params = {'source': 'NASA'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        # Should match "NASA Launches..." and "NASA News" source
        self.assertEqual(len(result), 2)

    def test_apply_filters_source_case_insensitive(self):
        """Test source filter is case insensitive"""
        filter_params = {'source': 'nasa'}
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        self.assertEqual(len(result), 2)

    def test_apply_filters_multiple_filters(self):
        """Test combining multiple filters"""
        filter_params = {
            'search_query': 'Space',
            'date_from': date(2024, 1, 12),
            'date_to': date(2024, 1, 22)
        }
        result = NewsFilterService.apply_filters(self.sample_articles, filter_params)
        
        # Should match "SpaceX Starship" and "International Space Station"
        self.assertGreaterEqual(len(result), 1)
        for article in result:
            self.assertIn('space', (article.get('title') or '').lower() + 
                         (article.get('description') or '').lower())

    def test_apply_filters_empty_article_list(self):
        """Test filtering empty article list"""
        result = NewsFilterService.apply_filters([], {'search_query': 'test'})
        self.assertEqual(len(result), 0)


class BuildAPIParamsTest(TestCase):
    """Tests for build_api_params method"""

    def setUp(self):
        """Set up base parameters"""
        self.base_params = {
            'q': 'space',
            'language': 'en',
            'pageSize': 20
        }

    def test_build_api_params_no_filters(self):
        """Test building API params with no filters"""
        result = NewsFilterService.build_api_params({}, self.base_params)
        
        self.assertEqual(result['q'], 'space')
        self.assertEqual(result['language'], 'en')
        self.assertEqual(result['pageSize'], 20)

    def test_build_api_params_preserves_base_params(self):
        """Test that base params are not mutated"""
        original_base = self.base_params.copy()
        NewsFilterService.build_api_params({'sort_by': 'publishedAt'}, self.base_params)
        
        self.assertEqual(self.base_params, original_base)

    def test_build_api_params_date_from(self):
        """Test date_from parameter"""
        filter_params = {'date_from': date(2024, 1, 15)}
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertEqual(result['from_param'], '2024-01-15')

    def test_build_api_params_date_to(self):
        """Test date_to parameter"""
        filter_params = {'date_to': date(2024, 1, 20)}
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertEqual(result['to'], '2024-01-20')

    def test_build_api_params_both_dates(self):
        """Test both date parameters"""
        filter_params = {
            'date_from': date(2024, 1, 15),
            'date_to': date(2024, 1, 20)
        }
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertEqual(result['from_param'], '2024-01-15')
        self.assertEqual(result['to'], '2024-01-20')

    def test_build_api_params_sort_by(self):
        """Test sort_by parameter"""
        filter_params = {'sort_by': 'publishedAt'}
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertEqual(result['sort_by'], 'publishedAt')

    def test_build_api_params_source_nasa(self):
        """Test NASA source filter modifies query"""
        filter_params = {'source': 'nasa'}
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertIn('NASA', result['q'])
        self.assertIn('rocket', result['q'])
        self.assertIn('satellite', result['q'])
        self.assertIn('AND', result['q'])

    def test_build_api_params_source_spacex(self):
        """Test SpaceX source filter modifies query"""
        filter_params = {'source': 'spacex'}
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertIn('SpaceX', result['q'])
        self.assertIn('rocket', result['q'])
        self.assertIn('starship', result['q'])
        self.assertIn('falcon', result['q'])

    def test_build_api_params_source_space(self):
        """Test space source filter modifies query"""
        filter_params = {'source': 'space'}
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertIn('space exploration', result['q'])
        self.assertIn('astronomy', result['q'])
        self.assertIn('OR', result['q'])

    def test_build_api_params_source_unknown(self):
        """Test unknown source doesn't modify query"""
        filter_params = {'source': 'unknown'}
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        # Should keep original query
        self.assertEqual(result['q'], 'space')

    def test_build_api_params_multiple_parameters(self):
        """Test combining multiple filter parameters"""
        filter_params = {
            'date_from': date(2024, 1, 15),
            'date_to': date(2024, 1, 20),
            'sort_by': 'popularity',
            'source': 'nasa'
        }
        result = NewsFilterService.build_api_params(filter_params, self.base_params)
        
        self.assertEqual(result['from_param'], '2024-01-15')
        self.assertEqual(result['to'], '2024-01-20')
        self.assertEqual(result['sort_by'], 'popularity')
        self.assertIn('NASA', result['q'])

    def test_build_api_params_empty_filter_params(self):
        """Test with empty filter params dict"""
        result = NewsFilterService.build_api_params({}, self.base_params)
        
        self.assertEqual(result, self.base_params)


class EdgeCaseTests(TestCase):
    """Tests for edge cases and error handling"""

    def test_article_missing_published_at(self):
        """Test handling articles without publishedAt"""
        articles = [
            {
                'title': 'Test Article',
                'description': 'Test description',
                # Missing publishedAt
            }
        ]
        
        filter_params = {'date_from': date(2024, 1, 15)}
        result = NewsFilterService.apply_filters(articles, filter_params)
        
        # Article without publishedAt should be filtered out
        self.assertEqual(len(result), 0)

    def test_article_missing_source(self):
        """Test handling articles without source"""
        articles = [
            {
                'title': 'NASA Mission',
                'description': 'Test description',
                'publishedAt': '2024-01-15T10:30:00Z',
                # Missing source
            }
        ]
        
        filter_params = {'source': 'nasa'}
        result = NewsFilterService.apply_filters(articles, filter_params)
        
        # Should still match on title
        self.assertEqual(len(result), 1)

    def test_article_all_null_fields(self):
        """Test handling articles with all null fields"""
        articles = [
            {
                'title': None,
                'description': None,
                'publishedAt': '2024-01-15T10:30:00Z',
                'source': None
            }
        ]
        
        filter_params = {'search_query': 'test'}
        result = NewsFilterService.apply_filters(articles, filter_params)
        
        # Should not match and not crash
        self.assertEqual(len(result), 0)

    def test_special_characters_in_search(self):
        """Test search with special characters"""
        articles = [
            {
                'title': 'SpaceX & NASA Collaboration',
                'description': 'Test (with) special [characters]',
                'publishedAt': '2024-01-15T10:30:00Z',
            }
        ]
        
        filter_params = {'search_query': 'SpaceX & NASA'}
        result = NewsFilterService.apply_filters(articles, filter_params)
        
        self.assertEqual(len(result), 1)

    def test_very_long_search_query(self):
        """Test with very long search query"""
        articles = [
            {
                'title': 'Short title',
                'description': 'Short description',
                'publishedAt': '2024-01-15T10:30:00Z',
            }
        ]
        
        filter_params = {'search_query': 'a' * 1000}
        result = NewsFilterService.apply_filters(articles, filter_params)
        
        # Should not crash, just return empty
        self.assertEqual(len(result), 0)
