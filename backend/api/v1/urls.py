"""
API v1 URLs configuration.
"""
from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Import viewsets (actualizados a la nueva estructura)
from modulos.modulo_estudiantes.views import EstudianteViewSet, CargaEstudiantesAPIView
from modulos.modulo_certificados.views import (
    EventoViewSet,
    CertificadoViewSet,
    GenerarCertificadosDesdeCSVAPIView,
    ValidarCertificadoAPIView,
    CertificadoPDFPublicAPIView,
    ExportarCertificadosZipAPIView,
    ConstanciaPublicAPIView,
)
from modulos.modulo_pagos.views import (
    PagoViewSet,
    CuotaViewSet,
    EstadoPagosEventoViewSet,
    MatriculaViewSet,
    BecaViewSet,
    DescuentoViewSet,
    PlanPagoViewSet,
)

# Router configuration
router = routers.DefaultRouter()
router.register(r'estudiantes', EstudianteViewSet, basename='estudiantes')
router.register(r'eventos', EventoViewSet, basename='eventos')
router.register(r'certificados', CertificadoViewSet, basename='certificados')
router.register(r'pagos', PagoViewSet, basename='pagos')
router.register(r'cuotas', CuotaViewSet, basename='cuotas')
router.register(r'planes-pago', PlanPagoViewSet, basename='planes-pago')
router.register(r'estados-pago', EstadoPagosEventoViewSet, basename='estados-pago')
router.register(r'matriculas', MatriculaViewSet, basename='matriculas')
router.register(r'becas', BecaViewSet, basename='becas')
router.register(r'descuentos', DescuentoViewSet, basename='descuentos')

urlpatterns = [
    # Special endpoints (ANTES del router para evitar conflictos)
    path('estudiantes/cargar-estudiantes/', CargaEstudiantesAPIView.as_view(), name='cargar-estudiantes'),
    path('cargar-certificados/', GenerarCertificadosDesdeCSVAPIView.as_view(), name='cargar_certificados'),
    path('certificados/validar/', ValidarCertificadoAPIView.as_view(), name='validar_certificado'),
    path('certificados/pdf/', CertificadoPDFPublicAPIView.as_view(), name='certificado_pdf_publico'),
    path('certificados/constancia/', ConstanciaPublicAPIView.as_view(), name='constancia_publica'),
    path('certificados/exportar_zip/', ExportarCertificadosZipAPIView.as_view(), name='exportar_certificados_zip'),
    
    # API endpoints (router)
    path('', include(router.urls)),
    
    # JWT endpoints
    path('auth/jwt/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/jwt/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
