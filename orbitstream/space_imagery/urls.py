from django.urls import path
from . import views

app_name = 'space_imagery'

urlpatterns = [
    path('', views.gallery, name='gallery'),
]