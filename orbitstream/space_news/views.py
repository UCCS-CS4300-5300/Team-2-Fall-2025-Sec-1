# space_news/views.py
from django.shortcuts import render
from newsapi import NewsApiClient
from django.conf import settings
from news_filter.forms import NewsFilterForm
from news_filter.filters import NewsFilterService

def nasa_news(request):
    """
    View to fetch and display NASA and SpaceX space news articles with filtering
    """
    # Initialize filter form with GET parameters
    filter_form = NewsFilterForm(request.GET or None)
    
    # Get filter parameters
    filter_params = {}
    if filter_form.is_valid():
        filter_params = {k: v for k, v in filter_form.cleaned_data.items() if v}
    
    try:
        # Initialize News API client
        newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)
        
        # Base parameters for News API
        base_params = {
            'q': '(NASA OR SpaceX OR "space exploration" OR "space mission") AND (rocket OR satellite OR astronaut OR spacecraft OR launch)',
            'qintitle': 'space OR NASA OR SpaceX',
            'language': 'en',
            'sort_by': 'publishedAt',
            'page_size': 30,  # Fetch more to account for filtering
            'exclude_domains': 'adult-sites.com,inappropriate-domain.com'
        }
        
        # Apply filter parameters to API call
        api_params = NewsFilterService.build_api_params(filter_params, base_params)
        
        # Fetch articles with updated parameters
        articles_data = newsapi.get_everything(**api_params)
        
        if articles_data['status'] == 'ok':
            # Your existing content filtering
            filtered_articles = []
            inappropriate_keywords = [
                'adult', 'porn', 'xxx', 'celebrity gossip',
                'dating', 'sexy', 'erotic'
            ]
            
            for article in articles_data['articles']:
                # Check title and description for inappropriate content
                title = (article.get('title') or '').lower()
                description = (article.get('description') or '').lower()
                content = (article.get('content') or '').lower()
                
                # Skip if contains inappropriate keywords
                if any(keyword in title or keyword in description or keyword in content
                       for keyword in inappropriate_keywords):
                    continue
                
                # Only include if it's genuinely about space/NASA/SpaceX
                if any(term in title or term in description
                       for term in ['nasa', 'spacex', 'space', 'rocket', 'satellite',
                                    'astronaut', 'spacecraft', 'launch', 'mars', 'moon']):
                    filtered_articles.append(article)
            
            # Apply user's filter parameters (search query, date range, etc.)
            if filter_params:
                filtered_articles = NewsFilterService.apply_filters(filtered_articles, filter_params)
            
            # Limit to top 20 after all filtering
            filtered_articles = filtered_articles[:20]
            
            context = {
                'articles': filtered_articles,
                'total_results': len(filtered_articles),
                'error': None,
                'filter_form': filter_form,
                'has_active_filters': bool(filter_params),
            }
        else:
            context = {
                'articles': [],
                'error': 'Failed to fetch articles',
                'filter_form': filter_form,
                'has_active_filters': bool(filter_params),
            }
            
    except Exception as e:
        context = {
            'articles': [],
            'error': f'An error occurred: {str(e)}',
            'filter_form': filter_form,
            'has_active_filters': bool(filter_params),
        }
    
    return render(request, 'space_news/nasa_news.html', context)