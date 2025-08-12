"""
Core views for the academic gestion system.
"""
from django.http import HttpResponse

def inicio(request):
    """Vista de inicio del sistema."""
    return HttpResponse("""
    <html>
    <head>
        <title>Academic Gestion</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 40px; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .link { color: #007bff; text-decoration: none; }
            .link:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Academic Gestion</h1>
                <p>Sistema de Gestión Académica Profesional</p>
            </div>
            
            <div class="section">
                <h2>🔧 Administración</h2>
                <p><a href="/admin/" class="link">Panel de Administración Django</a></p>
            </div>
            
            <div class="section">
                <h2>📚 API Documentation</h2>
                <p><a href="/swagger/" class="link">Swagger UI</a> - Documentación interactiva de la API</p>
                <p><a href="/redoc/" class="link">ReDoc</a> - Documentación alternativa de la API</p>
            </div>
            
            <div class="section">
                <h2>🌐 Módulos del Sistema</h2>
                <p><a href="/estudiantes/" class="link">Estudiantes</a> - Gestión de estudiantes</p>
                <p><a href="/certificados/" class="link">Certificados</a> - Gestión de certificados</p>
                <p><a href="/pagos/" class="link">Pagos</a> - Gestión de pagos</p>
            </div>
            
            <div class="section">
                <h2>📖 API Endpoints</h2>
                <p><a href="/api/v1/" class="link">API v1</a> - Endpoints de la API REST</p>
            </div>
        </div>
    </body>
    </html>
    """)
