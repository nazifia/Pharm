from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from . import settings
from django.conf.urls.static import static
from api.views import serve_service_worker

urlpatterns = [
    path('admin/', admin.site.urls),
    path('wholesale/', include('wholesale.urls', namespace='wholesale')),
    path('store/', include('store.urls', namespace='store')),
    path('', include('userauth.urls')),
    path('chat/', include('chat.urls')),
    path('notebook/', include('notebook.urls')),
    path('api/', include('api.urls')),

    # Serve service worker from root path with full scope control
    path('sw.js', serve_service_worker, name='service-worker'),

    # Favicon redirect to static file
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.svg', permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
