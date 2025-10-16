from django.urls import path
from . import views

app_name = 'space_news'

urlpatterns = [
    path('', views.nasa_news, name='nasa_news'),
]