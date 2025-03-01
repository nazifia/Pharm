
from django.contrib import admin 
from django.urls import path, include 
from . import settings
from django.conf.urls.static import static 

from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('', include('wholesale.urls')),
    path('', include('userauth.urls')),
    
     path('offline/', include('offline.urls')),
    # Service worker needs to be served from the root
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript'
    ), name='sw.js'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
