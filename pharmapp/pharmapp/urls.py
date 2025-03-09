import os
from django.contrib import admin 
from django.urls import path, include 
from . import settings
from django.conf.urls.static import static 
from django.contrib.staticfiles.views import serve

from django.views.generic import TemplateView


def serve_sw(request):
    sw_path = os.path.join(settings.STATIC_ROOT, 'js', 'sw.js')
    return serve(request, os.path.basename(sw_path), os.path.dirname(sw_path))



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('', include('wholesale.urls')),
    path('', include('userauth.urls')),
    
    path('api/', include('api.urls')),
    
    # path('sw.js', serve, {'path': 'js/sw.js'}),
    # Update the service worker path
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript'
    ), name='sw.js'),
    path('sw.js', serve_sw, name='service-worker'),
    
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
