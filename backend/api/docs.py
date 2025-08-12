"""
Configuración de Documentación de API para Gestion Academica
==========================================================

Configuración de Swagger/OpenAPI para documentar la API REST.
"""

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

# Configuración de la documentación de la API
schema_view = get_schema_view(
    openapi.Info(
        title="Gestion Academica API",
        default_version='v1',
        description="""
        # Sistema de Gestión Académica - API REST
        
        ## Descripción
        API completa para la gestión de estudiantes, certificados y pagos
        de la Universidad Técnica Estatal de Quevedo.
        
        ## Características
        - **Gestión de Estudiantes**: CRUD completo de estudiantes
        - **Generación de Certificados**: Creación y gestión de certificados
        - **Control de Pagos**: Sistema de pagos y facturación
        - **Autenticación**: Sistema de tokens JWT
        - **Documentación**: API completamente documentada
        
        ## Autenticación
        La API utiliza autenticación JWT. Incluye el header:
        ```
        Authorization: Bearer <access>
        ```
        
        ## Endpoints Principales
        
        ### Estudiantes
        - `GET /api/v1/estudiantes/` - Listar estudiantes
        - `POST /api/v1/estudiantes/` - Crear estudiante
        - `GET /api/v1/estudiantes/{id}/` - Obtener estudiante
        - `PUT /api/v1/estudiantes/{id}/` - Actualizar estudiante
        - `DELETE /api/v1/estudiantes/{id}/` - Eliminar estudiante
        
        ### Certificados
        - `GET /api/v1/certificados/` - Listar certificados
        - `POST /api/v1/certificados/` - Generar certificado
        - `GET /api/v1/certificados/{id}/` - Obtener certificado
        - `GET /api/v1/certificados/{id}/download/` - Descargar PDF
        
        ### Pagos
        - `GET /api/v1/pagos/` - Listar pagos
        - `POST /api/v1/pagos/` - Crear pago
        - `GET /api/v1/pagos/{id}/` - Obtener pago
        - `PUT /api/v1/pagos/{id}/` - Actualizar pago
        
        ## Códigos de Estado
        - `200` - OK - Petición exitosa
        - `201` - Created - Recurso creado
        - `400` - Bad Request - Error en la petición
        - `401` - Unauthorized - No autenticado
        - `403` - Forbidden - No autorizado
        - `404` - Not Found - Recurso no encontrado
        - `500` - Internal Server Error - Error del servidor
        
        ## Ejemplos de Uso
        
        ### Obtener tokens JWT
        ```bash
        curl -X POST "http://localhost:8000/api/v1/auth/jwt/" \\
             -H "Content-Type: application/json" \\
             -d '{
               "username": "admin",
               "password": "<password>"
             }'
        ```

        ### Crear un Estudiante
        ```bash
        curl -X POST "http://localhost:8000/api/v1/estudiantes/" \\
             -H "Authorization: Bearer <access>" \\
             -H "Content-Type: application/json" \\
             -d '{
               "cedula": "1234567890",
               "nombres": "Juan Carlos",
               "apellidos": "Pérez González",
               "email": "juan.perez@uteq.edu.ec",
               "telefono": "0987654321"
             }'
        ```
        
        ### Generar un Certificado
        ```bash
        curl -X POST "http://localhost:8000/api/v1/certificados/" \\
             -H "Authorization: Bearer <access>" \\
             -H "Content-Type: application/json" \\
             -d '{
               "estudiante": 1,
               "tipo": "diploma",
               "fecha_emision": "2025-01-15"
             }'
        ```
        
        ## Soporte
        Para soporte técnico, contacta a:
        - **Email**: bryphy@example.com
        - **Desarrollador**: Bryphy
        
        ## Licencia
        Este proyecto está bajo la licencia MIT.
        """,
        terms_of_service="https://www.uteq.edu.ec/terms/",
        contact=openapi.Contact(
            name="Bryphy",
            email="bryphy@example.com",
            url="https://github.com/bryphy"
        ),
        license=openapi.License(
            name="MIT License",
            url="https://opensource.org/licenses/MIT"
        ),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=[
        # Aquí se pueden agregar patrones específicos si es necesario
    ],
)

# Configuración adicional de Swagger
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        # Nota: drf-yasg (OpenAPI 2.0) usa apiKey para headers; documentamos formato Bearer
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT en el header Authorization con formato: Bearer <access>'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': [
        'get',
        'post',
        'put',
        'delete',
        'patch'
    ],
    'OPERATIONS_SORTER': 'alpha',
    'TAGS_SORTER': 'alpha',
    'DOC_EXPANSION': 'none',
    'DEEP_LINKING': True,
    'DISPLAY_OPERATION_ID': False,
    'DEFAULT_MODEL_RENDERING': 'example',
    'DEFAULT_INFO': 'Gestion Academica API v1',
    'DEFAULT_API_URL': 'http://localhost:8000/api/v1/',
    # Marcar Bearer como esquema por defecto en UI (documental)
    'SECURITY_REQUIREMENTS': [{ 'Bearer': [] }],
}

# Configuración de Redoc (alternativa a Swagger UI)
REDOC_SETTINGS = {
    'LAZY_RENDERING': False,
    'HIDE_HOSTNAME': False,
    'HIDE_LOADING': False,
    'HIDE_DOWNLOAD_BUTTON': False,
    'HIDE_SINGLE_REQUEST_SAMPLE_TAB': False,
    'HIDE_MULTI_REQUEST_SAMPLE_TAB': False,
    'HIDE_SCHEMA_TAB': False,
    'HIDE_RESPONSE_EXAMPLES': False,
    'HIDE_REQUEST_HEADERS': False,
    'HIDE_RESPONSE_HEADERS': False,
    'HIDE_HOSTNAME': False,
    'HIDE_LOADING': False,
    'HIDE_DOWNLOAD_BUTTON': False,
    'HIDE_SINGLE_REQUEST_SAMPLE_TAB': False,
    'HIDE_MULTI_REQUEST_SAMPLE_TAB': False,
    'HIDE_SCHEMA_TAB': False,
    'HIDE_RESPONSE_EXAMPLES': False,
    'HIDE_REQUEST_HEADERS': False,
    'HIDE_RESPONSE_HEADERS': False,
}

# Configuración de endpoints de documentación
API_DOCS_URLS = {
    'swagger': 'swagger/',
    'redoc': 'redoc/',
    'json': 'swagger.json',
    'yaml': 'swagger.yaml',
}

# Configuración de grupos de endpoints para la documentación
API_TAGS = [
    {
        'name': 'estudiantes',
        'description': 'Operaciones relacionadas con la gestión de estudiantes',
        'externalDocs': {
            'description': 'Documentación adicional',
            'url': 'https://docs.uteq.edu.ec/estudiantes/',
        },
    },
    {
        'name': 'certificados',
        'description': 'Operaciones para la generación y gestión de certificados',
        'externalDocs': {
            'description': 'Documentación adicional',
            'url': 'https://docs.uteq.edu.ec/certificados/',
        },
    },
    {
        'name': 'pagos',
        'description': 'Operaciones para el control de pagos y facturación',
        'externalDocs': {
            'description': 'Documentación adicional',
            'url': 'https://docs.uteq.edu.ec/pagos/',
        },
    },
    {
        'name': 'autenticacion',
        'description': 'Operaciones de autenticación y autorización',
    },
    {
        'name': 'utilidades',
        'description': 'Endpoints de utilidad y sistema',
    },
]
