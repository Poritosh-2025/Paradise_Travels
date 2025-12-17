"""
Main URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Endpoints
    path('api/', include('authentication.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/user-management/', include('user_management.urls')),
    path('api/administrators/', include('administrators.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/api-management/', include('api_management.urls')),
    path('api/ai/', include('ai_services.urls')),  # AI Services endpoints

]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
