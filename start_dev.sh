#!/bin/bash

# Script de inicio rápido para Gestion Academica
# ==============================================

echo "🚀 Iniciando Sistema de Gestión Académica..."
echo "=========================================="

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor, instala Docker primero."
    exit 1
fi

# Verificar si Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado. Por favor, instala Docker Compose primero."
    exit 1
fi

# Función para mostrar el estado de los servicios
show_status() {
    echo ""
    echo "📊 Estado de los servicios:"
    docker-compose ps
    echo ""
    echo "🌐 URLs del sistema:"
    echo "   - Backend Django: http://localhost:8000"
    echo "   - Admin Django:   http://localhost:8000/admin/"
    echo "   - API REST:       http://localhost:8000/api/v1/"
    echo "   - Swagger:        http://localhost:8000/swagger/"
    echo "   - Health Check:   http://localhost:8000/_healthz/"
    echo ""
}

# Función para detener servicios
stop_services() {
    echo "🛑 Deteniendo servicios..."
    docker-compose down
    echo "✅ Servicios detenidos."
}

# Función para reiniciar servicios
restart_services() {
    echo "🔄 Reiniciando servicios..."
    docker-compose restart
    echo "✅ Servicios reiniciados."
    show_status
}

# Función para ver logs
show_logs() {
    echo "📋 Mostrando logs del backend..."
    docker-compose logs -f backend
}

# Función para ejecutar comandos Django
django_command() {
    if [ -z "$1" ]; then
        echo "❌ Debes especificar un comando Django."
        echo "   Ejemplo: ./start_dev.sh django migrate"
        exit 1
    fi
    
    echo "🐍 Ejecutando comando Django: $*"
    docker-compose exec backend python manage.py "$@"
}

# Función para crear superusuario
create_superuser() {
    echo "👤 Creando superusuario..."
    docker-compose exec backend python manage.py createsuperuser
}

# Función para ejecutar tests
run_tests() {
    echo "🧪 Ejecutando tests..."
    docker-compose exec backend python manage.py test
}

# Función para limpiar Docker
clean_docker() {
    echo "🧹 Limpiando contenedores y volúmenes..."
    docker-compose down -v
    docker system prune -f
    echo "✅ Limpieza completada."
}

# Función para mostrar ayuda
show_help() {
    echo "📖 Uso: ./start_dev.sh [COMANDO]"
    echo ""
    echo "Comandos disponibles:"
    echo "  start          - Iniciar todos los servicios"
    echo "  stop           - Detener todos los servicios"
    echo "  restart        - Reiniciar todos los servicios"
    echo "  status         - Mostrar estado de los servicios"
    echo "  logs           - Mostrar logs del backend"
    echo "  test_endpoints - Ejecutar pruebas de endpoints (Django test runner)"
    echo "  test_endpoints_certificados - Pruebas de endpoints: Certificados"
    echo "  test_endpoints_estudiantes  - Pruebas de endpoints: Estudiantes"
    echo "  test_endpoints_pagos        - Pruebas de endpoints: Pagos"
    echo "  test_endpoints_all          - Pruebas de endpoints: Todos"
    echo "  django [CMD]   - Ejecutar comando Django"
    echo "  superuser      - Crear superusuario"
    echo "  test           - Ejecutar tests"
    echo "  clean          - Limpiar Docker (contenedores y volúmenes)"
    echo "  help           - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  ./start_dev.sh start"
    echo "  ./start_dev.sh django migrate"
    echo "  ./start_dev.sh django shell"
    echo "  ./start_dev.sh clean"
}

# Función principal para iniciar servicios
start_services() {
    echo "🔧 Construyendo y iniciando servicios..."
    
    # Verificar si existe archivo backend/.env
    if [ ! -f "backend/.env" ]; then
        echo "⚠️  No se encontró archivo backend/.env, copiando desde backend/env.example..."
        cp backend/env.example backend/.env
        echo "✅ Archivo backend/.env creado. Revisa y configura las variables si es necesario."
    fi
    
    # Construir imágenes solo si no existen o si han cambiado
    echo "🔨 Verificando imágenes Docker..."
    if docker-compose images | grep -q "gestion-academica-backend"; then
        echo "✅ Imagen del backend ya existe. Usando caché..."
        docker-compose build
    else
        echo "🔨 Construyendo imagen del backend..."
        docker-compose build
    fi
    
    # Iniciar servicios
    echo "🚀 Iniciando servicios..."
    docker-compose up -d
    
    # Esperar a que el backend esté listo
    echo "⏳ Esperando a que el backend esté listo..."
    sleep 15
    
    # Verificar estado de salud
    echo "🏥 Verificando estado de salud del backend..."
    if curl -f http://localhost:8000/_healthz/ > /dev/null 2>&1; then
        echo "✅ Backend está funcionando correctamente."
    else
        echo "⚠️  Backend puede no estar completamente listo. Revisa los logs con './start_dev.sh logs'"
    fi
    
    echo "✅ ¡Sistema iniciado correctamente!"
    show_status
}

# Procesar argumentos de línea de comandos
case "${1:-start}" in
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "django")
        shift
        django_command "$@"
        ;;
    "superuser")
        create_superuser
        ;;
    "test")
        run_tests
        ;;
  "test_endpoints")
    echo "🧪 Ejecutando pruebas de endpoints (Django test runner)..."
    docker-compose exec backend python manage.py test modulos.modulo_certificados.tests_endpoints -v 2
    ;;
  "test_endpoints_certificados")
    echo "🧪 Certificados: pruebas de endpoints..."
    docker-compose exec backend python manage.py test modulos.modulo_certificados.tests_endpoints -v 2
    ;;
  "test_endpoints_estudiantes")
    echo "🧪 Estudiantes: pruebas de endpoints..."
    docker-compose exec backend python manage.py test modulos.modulo_estudiantes.tests_endpoints -v 2
    ;;
  "test_endpoints_pagos")
    echo "🧪 Pagos: pruebas de endpoints..."
    docker-compose exec backend python manage.py test modulos.modulo_pagos.tests_endpoints -v 2
    ;;
  "test_endpoints_all")
    echo "🧪 Ejecutando TODAS las pruebas de endpoints..."
    docker-compose exec backend python manage.py test \
      modulos.modulo_certificados.tests_endpoints \
      modulos.modulo_estudiantes.tests_endpoints \
      modulos.modulo_pagos.tests_endpoints -v 2
    ;;
    "clean")
        clean_docker
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Comando desconocido: $1"
        echo "   Usa './start_dev.sh help' para ver comandos disponibles."
        exit 1
        ;;
esac
