"""
URL configuration for orbitstream project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from home.views import index  # Import from home app

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),                      # Your index view
    path('news/', include('space_news.urls')),          # space news page path
    path('', include('users.urls')),                    # register and login page paths
    path('gallery/', include('space_imagery.urls')),     # gallery page path
    path('satellite-tracking/', include('satellite_tracking.urls')),  # satellite tracking page path
    path('learn_page/', include('learn_page.urls')),  # learn page path
]
