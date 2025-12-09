from django.urls import path
from . import views

app_name = 'satellite_tracking'

urlpatterns = [
    path('closest-satellite/', views.closest_satellite, name='closest_satellite'),
    path('api/get-closest-satellite/', views.get_closest_satellite_api, name='get_closest_satellite_api'),
    path('api/get-satellite-position/', views.get_satellite_position_api, name='get_satellite_position_api'),
]
