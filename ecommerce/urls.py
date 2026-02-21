from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('shop/', include('shop.urls')),
    path('chat/', include('chat.urls')),
    path('feed/', include('feed.urls')),
    path('notifications/', include('notifications.urls')),
    path('community/', include('community.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)