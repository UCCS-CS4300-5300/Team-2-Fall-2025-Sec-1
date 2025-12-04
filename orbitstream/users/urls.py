from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name='register_view'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('settings/', views.settings_view, name='settings'),
    path('presets/create/', views.create_preset, name='create_preset'),
    path('presets/<int:preset_id>/edit/', views.edit_preset, name='edit_preset'),
    path('presets/<int:preset_id>/delete/', views.delete_preset, name='delete_preset'),
    path('presets/<int:preset_id>/get/', views.get_preset, name='get_preset'),
]