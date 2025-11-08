# news_filters/filters.py
from datetime import datetime

class NewsFilterService:
    """Service class to handle news filtering logic"""
    
    @staticmethod
    def apply_filters(articles, filter_params):
        """
        Apply filters to a list of articles
        
        Args:
            articles: List of article dictionaries from News API
            filter_params: Dictionary of filter parameters from form
        
        Returns:
            Filtered list of articles
        """
        filtered = articles
        
        # Search query filter (search in title and description)
        if filter_params.get('search_query'):
            query = filter_params['search_query'].lower().strip()
            filtered = [
                article for article in filtered
                if query in (article.get('title') or '').lower() or
                   query in (article.get('description') or '').lower()
            ]
        
        # Date range filter
        if filter_params.get('date_from'):
            date_from = filter_params['date_from']
            filtered = [
                article for article in filtered
                if article.get('publishedAt') and 
                   datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')).date() >= date_from
            ]
        
        if filter_params.get('date_to'):
            date_to = filter_params['date_to']
            filtered = [
                article for article in filtered
                if article.get('publishedAt') and
                   datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')).date() <= date_to
            ]
        
        # Source filter
        if filter_params.get('source'):
            source_filter = filter_params['source'].lower()
            filtered = [
                article for article in filtered
                if source_filter in (article.get('title') or '').lower() or
                   source_filter in (article.get('description') or '').lower() or
                   source_filter in (article.get('source', {}).get('name') or '').lower()
            ]
        
        return filtered
    
    @staticmethod
    def build_api_params(filter_params, base_params):
        """
        Build API parameters from filter form data
        Modifies the base_params dict with filter-specific parameters
        
        Args:
            filter_params: Dictionary of filter parameters from form
            base_params: Base NewsAPI parameters
        
        Returns:
            Updated parameters dict
        """
        api_params = base_params.copy()
        
        # Date filters - NewsAPI format
        if filter_params.get('date_from'):
            api_params['from_param'] = filter_params['date_from'].isoformat()
        
        if filter_params.get('date_to'):
            api_params['to'] = filter_params['date_to'].isoformat()
        
        # Sort by parameter
        if filter_params.get('sort_by'):
            api_params['sort_by'] = filter_params['sort_by']
        
        # Modify query based on source filter
        if filter_params.get('source'):
            source = filter_params['source']
            if source == 'nasa':
                api_params['q'] = 'NASA AND (rocket OR satellite OR astronaut OR spacecraft OR launch OR mission)'
            elif source == 'spacex':
                api_params['q'] = 'SpaceX AND (rocket OR launch OR starship OR falcon OR dragon)'
            elif source == 'space':
                api_params['q'] = '"space exploration" OR "space mission" OR astronomy OR satellite'
        
        return api_params