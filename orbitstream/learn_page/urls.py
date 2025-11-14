# learn_page/urls.py
from django.urls import path
from . import views

app_name = 'learn_page'

urlpatterns = [
    path('', views.learn_page, name='learn_page'),
    path('generate-summary/', views.generate_summary, name='generate_summary'),
]