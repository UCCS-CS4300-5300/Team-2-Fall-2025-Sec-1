from django.urls import path
from . import views

app_name = 'saved_page'

urlpatterns = [
    path('', views.saved_page, name='saved_page'),

    # Toggle save/unsave endpoints
    path('api/toggle/satellite/', views.toggle_save_satellite, name='toggle_save_satellite'),
    path('api/toggle/gallery/', views.toggle_save_gallery, name='toggle_save_gallery'),
    path('api/toggle/launch/', views.toggle_save_launch, name='toggle_save_launch'),
    path('api/toggle/learn/', views.toggle_save_learn, name='toggle_save_learn'),
    path('api/toggle/news/', views.toggle_save_news, name='toggle_save_news'),

    # Check if saved endpoints
    path('api/check/satellite/', views.check_saved_satellite, name='check_saved_satellite'),
    path('api/check/gallery/', views.check_saved_gallery, name='check_saved_gallery'),
    path('api/check/launch/', views.check_saved_launch, name='check_saved_launch'),
    path('api/check/learn/', views.check_saved_learn, name='check_saved_learn'),
    path('api/check/news/', views.check_saved_news, name='check_saved_news'),

    # Get all saved IDs (for batch checking)
    path('api/saved-ids/', views.get_saved_ids, name='get_saved_ids'),

    # Delete endpoints
    path('api/delete/satellite/<int:pk>/', views.delete_saved_satellite, name='delete_saved_satellite'),
    path('api/delete/gallery/<int:pk>/', views.delete_saved_gallery, name='delete_saved_gallery'),
    path('api/delete/launch/<int:pk>/', views.delete_saved_launch, name='delete_saved_launch'),
    path('api/delete/learn/<int:pk>/', views.delete_saved_learn, name='delete_saved_learn'),
    path('api/delete/news/<int:pk>/', views.delete_saved_news, name='delete_saved_news'),
]
