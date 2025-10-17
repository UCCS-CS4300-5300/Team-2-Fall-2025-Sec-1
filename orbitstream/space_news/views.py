from django.shortcuts import render
from newsapi import NewsApiClient
from django.conf import settings

def nasa_news(request):
    """
    View to fetch and display NASA space news articles
    """
    try:
        # Initialize News API client
        newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)
        
        # Fetch articles
        articles_data = newsapi.get_everything(
            q='NASA space',
            language='en',
            sort_by='publishedAt',
            page_size=10
        )
        
        if articles_data['status'] == 'ok':
            articles = articles_data['articles']
            context = {
                'articles': articles,
                'total_results': articles_data.get('totalResults', 0),
                'error': None
            }
        else:
            context = {
                'articles': [],
                'error': 'Failed to fetch articles'
            }
            
    except Exception as e:
        context = {
            'articles': [],
            'error': f'An error occurred: {str(e)}'
        }
    
    return render(request, 'space_news/nasa_news.html', context)