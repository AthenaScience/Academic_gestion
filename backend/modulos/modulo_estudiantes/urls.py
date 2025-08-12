from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EstudianteViewSet, CargaEstudiantesAPIView

# Este router ya no es necesario ya que las URLs están en api/v1/urls.py
# Se mantiene por compatibilidad pero las URLs principales están en la API

urlpatterns = [
    # Las URLs principales están en api/v1/urls.py
    # Este archivo se mantiene por compatibilidad
    
    # Solo mantenemos endpoints especiales que no están en la API principal
    path('estudiantes/cargar-estudiantes/', CargaEstudiantesAPIView.as_view(), name='cargar-estudiantes'),
]