#!/bin/bash

# 🏭 SCRIPT DE PRODUCCIÓN - Sistema de Gestión Académica
# Funciona tanto en Docker como en instalación directa en servidor

set -e  # Salir si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con colores
print_status() {
    echo -e "${BLUE}🏭 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Función de ayuda
show_help() {
    echo "🏭 SCRIPT DE PRODUCCIÓN - Sistema de Gestión Académica"
    echo "=================================================="
    echo ""
    echo "USO: ./start_prod.sh [COMANDO]"
    echo ""
    echo "COMANDOS DISPONIBLES:"
    echo "  start       - Iniciar servicios de producción"
    echo "  stop        - Detener servicios de producción"
    echo "  restart     - Reiniciar servicios de producción"
    echo "  status      - Estado de los servicios"
    echo "  logs        - Ver logs en tiempo real"
    echo "  deploy      - Desplegar nueva versión"
    echo "  backup      - Crear backup de la base de datos"
    echo "  update      - Actualizar código desde Git"
    echo "  health      - Verificar salud del sistema"
    echo "  help        - Mostrar esta ayuda"
    echo ""
    echo "MODO DE OPERACIÓN:"
    echo "  - Si detecta Docker: usa docker-compose.prod.yml"
    echo "  - Si no hay Docker: usa servicios del sistema"
    echo ""
    echo "EJEMPLOS:"
    echo "  ./start_prod.sh start    # Iniciar producción"
    echo "  ./start_prod.sh deploy   # Desplegar nueva versión"
    echo "  ./start_prod.sh health   # Verificar sistema"
}

# Función para detectar el entorno
detect_environment() {
    if command -v docker &> /dev/null && [ -f "docker-compose.prod.yml" ]; then
        echo "docker"
    elif command -v systemctl &> /dev/null; then
        echo "systemd"
    elif command -v supervisorctl &> /dev/null; then
        echo "supervisor"
    else
        echo "manual"
    fi
}

# Función para verificar si Docker está disponible
check_docker() {
    if command -v docker &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Función para verificar si docker-compose está disponible
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Función para iniciar con Docker
start_docker() {
    print_status "Iniciando servicios con Docker..."
    
    if ! check_docker; then
        print_error "Docker no está instalado"
        exit 1
    fi
    
    if ! check_docker_compose; then
        print_error "Docker Compose no está instalado"
        exit 1
    fi
    
    # Verificar que existe el archivo de producción
    if [ ! -f "docker-compose.prod.yml" ]; then
        print_error "No se encontró docker-compose.prod.yml"
        exit 1
    fi
    
    # Iniciar servicios
    docker-compose -f docker-compose.prod.yml up -d
    
    print_success "Servicios iniciados con Docker"
    print_status "Verificando salud del sistema..."
    sleep 10
    
    # Verificar salud
    if curl -f http://localhost:8000/_healthz/ > /dev/null 2>&1; then
        print_success "Sistema funcionando correctamente"
    else
        print_warning "Sistema iniciado pero health check falló"
    fi
}

# Función para iniciar con systemd
start_systemd() {
    print_status "Iniciando servicios con systemd..."
    
    # Verificar si el servicio existe
    if systemctl list-unit-files | grep -q "gestion-academica"; then
        sudo systemctl start gestion-academica
        sudo systemctl enable gestion-academica
        print_success "Servicio gestion-academica iniciado"
    else
        print_warning "Servicio systemd no encontrado, creando..."
        create_systemd_service
    fi
}

# Función para crear servicio systemd
create_systemd_service() {
    print_status "Creando servicio systemd..."
    
    # Crear archivo de servicio
    sudo tee /etc/systemd/system/gestion-academica.service > /dev/null <<EOF
[Unit]
Description=Sistema de Gestión Académica
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$(pwd)
Environment=DJANGO_SETTINGS_MODULE=gestion_academica.settings
Environment=DJANGO_DEBUG=False
ExecStart=/usr/bin/gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 gestion_academica.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable gestion-academica
    sudo systemctl start gestion-academica
    
    print_success "Servicio systemd creado e iniciado"
}

# Función para iniciar con supervisor
start_supervisor() {
    print_status "Iniciando servicios con supervisor..."
    
    if [ -f "/etc/supervisor/conf.d/gestion-academica.conf" ]; then
        sudo supervisorctl start gestion-academica
        print_success "Servicio supervisor iniciado"
    else
        print_warning "Configuración de supervisor no encontrada"
        print_status "Usando modo manual..."
        start_manual
    fi
}

# Función para iniciar manualmente
start_manual() {
    print_status "Iniciando servicios manualmente..."
    
    # Verificar si ya está corriendo
    if pgrep -f "gunicorn.*gestion_academica" > /dev/null; then
        print_warning "Servicio ya está corriendo"
        return
    fi
    
    # Iniciar en background
    nohup gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 gestion_academica.wsgi:application > logs/gunicorn.log 2>&1 &
    
    print_success "Servicio iniciado manualmente (PID: $!)"
    print_warning "Para detener: kill $!"
}

# Función para detener servicios
stop_services() {
    local env=$(detect_environment)
    
    case $env in
        "docker")
            print_status "Deteniendo servicios Docker..."
            docker-compose -f docker-compose.prod.yml down
            print_success "Servicios Docker detenidos"
            ;;
        "systemd")
            print_status "Deteniendo servicios systemd..."
            sudo systemctl stop gestion-academica
            print_success "Servicios systemd detenidos"
            ;;
        "supervisor")
            print_status "Deteniendo servicios supervisor..."
            sudo supervisorctl stop gestion-academica
            print_success "Servicios supervisor detenidos"
            ;;
        *)
            print_status "Deteniendo servicios manuales..."
            pkill -f "gunicorn.*gestion_academica" || true
            print_success "Servicios manuales detenidos"
            ;;
    esac
}

# Función para mostrar estado
show_status() {
    local env=$(detect_environment)
    
    echo "🏭 ESTADO DEL SISTEMA DE PRODUCCIÓN"
    echo "=================================="
    echo ""
    
    case $env in
        "docker")
            echo "🔧 Entorno: Docker"
            docker-compose -f docker-compose.prod.yml ps
            ;;
        "systemd")
            echo "🔧 Entorno: systemd"
            systemctl status gestion-academica --no-pager -l
            ;;
        "supervisor")
            echo "🔧 Entorno: supervisor"
            supervisorctl status gestion-academica
            ;;
        *)
            echo "🔧 Entorno: Manual"
            if pgrep -f "gunicorn.*gestion_academica" > /dev/null; then
                echo "✅ Servicio corriendo (PID: $(pgrep -f 'gunicorn.*gestion_academica'))"
            else
                echo "❌ Servicio no está corriendo"
            fi
            ;;
    esac
    
    echo ""
    echo "🌐 Verificando endpoints..."
    
    # Health check
    if curl -f http://localhost:8000/_healthz/ > /dev/null 2>&1; then
        echo "✅ Health check: OK"
    else
        echo "❌ Health check: FALLÓ"
    fi
    
    # API check
    if curl -f http://localhost:8000/api/v1/ > /dev/null 2>&1; then
        echo "✅ API: OK"
    else
        echo "❌ API: FALLÓ"
    fi
}

# Función para mostrar logs
show_logs() {
    local env=$(detect_environment)
    
    case $env in
        "docker")
            print_status "Mostrando logs de Docker..."
            docker-compose -f docker-compose.prod.yml logs -f
            ;;
        "systemd")
            print_status "Mostrando logs de systemd..."
            sudo journalctl -u gestion-academica -f
            ;;
        "supervisor")
            print_status "Mostrando logs de supervisor..."
            sudo supervisorctl tail -f gestion-academica
            ;;
        *)
            print_status "Mostrando logs manuales..."
            if [ -f "logs/gunicorn.log" ]; then
                tail -f logs/gunicorn.log
            else
                print_warning "No se encontraron logs"
            fi
            ;;
    esac
}

# Función para desplegar
deploy() {
    print_status "🚀 INICIANDO DESPLIEGUE DE PRODUCCIÓN..."
    
    # Verificar Git
    if [ ! -d ".git" ]; then
        print_error "No es un repositorio Git"
        exit 1
    fi
    
    # Backup antes del despliegue
    print_status "Creando backup..."
    ./start_prod.sh backup
    
    # Actualizar código
    print_status "Actualizando código desde Git..."
    git pull origin main || git pull origin master
    
    # Instalar dependencias
    print_status "Instalando dependencias..."
    pip install -r backend/requirements.txt
    
    # Migraciones
    print_status "Ejecutando migraciones..."
    cd backend
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    cd ..
    
    # Reiniciar servicios
    print_status "Reiniciando servicios..."
    ./start_prod.sh restart
    
    print_success "🚀 DESPLIEGUE COMPLETADO EXITOSAMENTE!"
}

# Función para backup
backup() {
    print_status "💾 Creando backup de la base de datos..."
    
    # Crear directorio de backups si no existe
    mkdir -p backups
    
    # Backup de SQLite (si existe)
    if [ -f "backend/db.sqlite3" ]; then
        cp backend/db.sqlite3 "backups/db_$(date +%Y%m%d_%H%M%S).sqlite3"
        print_success "Backup de SQLite creado"
    fi
    
    # Backup de archivos media
    if [ -d "media" ]; then
        tar -czf "backups/media_$(date +%Y%m%d_%H%M%S).tar.gz" media/
        print_success "Backup de media creado"
    fi
    
    print_success "Backup completado en directorio 'backups/'"
}

# Función para actualizar código
update_code() {
    print_status "📥 Actualizando código desde Git..."
    
    if [ ! -d ".git" ]; then
        print_error "No es un repositorio Git"
        exit 1
    fi
    
    git pull origin main || git pull origin master
    print_success "Código actualizado"
}

# Función para verificar salud
check_health() {
    print_status "🏥 Verificando salud del sistema..."
    
    # Health check del sistema
    if curl -f http://localhost:8000/_healthz/ > /dev/null 2>&1; then
        print_success "Health check: OK"
        curl -s http://localhost:8000/_healthz/ | jq . 2>/dev/null || curl -s http://localhost:8000/_healthz/
    else
        print_error "Health check: FALLÓ"
        exit 1
    fi
    
    # Verificar endpoints críticos
    print_status "Verificando endpoints críticos..."
    
    endpoints=(
        "http://localhost:8000/api/v1/"
        "http://localhost:8000/admin/"
        "http://localhost:8000/swagger/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f "$endpoint" > /dev/null 2>&1; then
            print_success "$endpoint: OK"
        else
            print_error "$endpoint: FALLÓ"
        fi
    done
    
    print_success "🏥 Verificación de salud completada"
}

# Función principal
main() {
    local command=${1:-"help"}
    
    case $command in
        "start")
            local env=$(detect_environment)
            case $env in
                "docker") start_docker ;;
                "systemd") start_systemd ;;
                "supervisor") start_supervisor ;;
                *) start_manual ;;
            esac
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            print_status "Reiniciando servicios..."
            stop_services
            sleep 2
            main start
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "deploy")
            deploy
            ;;
        "backup")
            backup
            ;;
        "update")
            update_code
            ;;
        "health")
            check_health
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Ejecutar función principal
main "$@"
