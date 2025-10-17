from django.urls import path
from .views import index

app_name = 'space_news' 

urlpatterns = [
    path('', index, name='index'),
    path('nasa-news/', views.nasa_news, name='nasa_news')  
]