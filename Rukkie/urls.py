"""
URL configuration for Rukkie project.

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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    # redirect bare /admin to /admin/ so Django's admin path is matched
    path('admin', RedirectView.as_view(url='/admin/')),
    path('api/', include('store.urls')),
    # Serve the SPA entry point for the root
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]

SERVE_MEDIA = settings.DEBUG or os.environ.get('SERVE_MEDIA', '').strip().lower() in ('1', 'true', 'yes', 'on')
if SERVE_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all: keep this LAST so it does not swallow media/static/admin/api routes.
urlpatterns += [
    re_path(
        r'^(?!api/|admin/|admin$|media/|static/).*$', 
        TemplateView.as_view(template_name='index.html')
    ),
]
