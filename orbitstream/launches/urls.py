from django.urls import path
from . import views

app_name = 'launches'

urlpatterns = [
    path('', views.show_launches, name='launch')
]