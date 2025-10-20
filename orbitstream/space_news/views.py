from django.shortcuts import render
from newsapi import NewsApiClient
from django.conf import settings

def nasa_news(request):
    """
    View to fetch and display NASA and SpaceX space news articles
    """
    try:
        # Initialize News API client
        newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)
       
        # Fetch articles with more specific query and exclusions
        articles_data = newsapi.get_everything(
            q='(NASA OR SpaceX OR "space exploration" OR "space mission") AND (rocket OR satellite OR astronaut OR spacecraft OR launch)',
            qintitle='space OR NASA OR SpaceX',  # Require these terms in title
            language='en',
            sort_by='publishedAt',
            page_size=20,  # Fetch more to account for filtering
            exclude_domains='adult-sites.com,inappropriate-domain.com'  # Add specific domains to exclude
        )
       
        if articles_data['status'] == 'ok':
            # Filter articles by content
            filtered_articles = []
            inappropriate_keywords = [
                'adult', 'porn', 'xxx', 'celebrity gossip', 
                'dating', 'sexy', 'erotic'
                # Add other terms you want to filter out
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
                    
                    # Stop when we have 10 good articles
                    if len(filtered_articles) >= 10:
                        break
            
            context = {
                'articles': filtered_articles,
                'total_results': len(filtered_articles),
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