"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve
from pathlib import Path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.http import JsonResponse, HttpResponse
from .views import inicio
from gestion_academica.monitoring import get_system_health, metrics_exporter

# Swagger/ReDoc configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Academic Gestion API",
        default_version='v1',
        description="API para gestión académica de eventos y certificados",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@academicgestion.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Home page
    path('', inicio, name='inicio'),
    
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API v1 - TODOS los endpoints están aquí
    path('api/v1/', include('api.v1.urls')),
    
    # Health and metrics
    path('_healthz/', lambda request: JsonResponse(get_system_health()), name='healthz'),
    path('_metrics/', lambda request: HttpResponse(metrics_exporter.export_prometheus_format(), content_type='text/plain'), name='metrics'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Servir carpeta 'public/' del repo en desarrollo via backend (útil para testers)
    # Servir carpeta backend/public dentro del contenedor
    public_dir = Path(settings.BASE_DIR) / 'public'
    urlpatterns += [
        re_path(r'^public/(?P<path>.*)$', static_serve, {'document_root': str(public_dir)}),
    ]