#!/bin/bash

# Script de Despliegue para Gestion Academica
# ===========================================
# Este script automatiza el despliegue en producción

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para mostrar ayuda
show_help() {
    echo "Script de Despliegue para Gestion Academica"
    echo ""
    echo "Uso: $0 [OPCIONES]"
    echo ""
    echo "OPCIONES:"
    echo "  -h, --help           Mostrar esta ayuda"
    echo "  -e, --environment    Ambiente de despliegue (staging/production)"
    echo "  -b, --backup         Crear backup antes del despliegue"
    echo "  -m, --migrate        Ejecutar migraciones"
    echo "  -c, --collectstatic  Recolectar archivos estáticos"
    echo "  -r, --restart        Reiniciar servicios"
    echo "  -f, --full           Despliegue completo (backup + migrate + collectstatic + restart)"
    echo ""
    echo "EJEMPLOS:"
    echo "  $0 --full --environment production"
    echo "  $0 --migrate --collectstatic"
    echo "  $0 --backup --environment staging"
}

# Variables por defecto
ENVIRONMENT="production"
CREATE_BACKUP=false
RUN_MIGRATIONS=false
COLLECT_STATIC=false
RESTART_SERVICES=false
FULL_DEPLOY=false

# Parsear argumentos de línea de comandos
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        -m|--migrate)
            RUN_MIGRATIONS=true
            shift
            ;;
        -c|--collectstatic)
            COLLECT_STATIC=true
            shift
            ;;
        -r|--restart)
            RESTART_SERVICES=true
            shift
            ;;
        -f|--full)
            FULL_DEPLOY=true
            shift
            ;;
        *)
            print_error "Opción desconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Si es despliegue completo, activar todas las opciones
if [ "$FULL_DEPLOY" = true ]; then
    CREATE_BACKUP=true
    RUN_MIGRATIONS=true
    COLLECT_STATIC=true
    RESTART_SERVICES=true
fi

# Verificar que al menos una opción esté seleccionada
if [ "$CREATE_BACKUP" = false ] && [ "$RUN_MIGRATIONS" = false ] && [ "$COLLECT_STATIC" = false ] && [ "$RESTART_SERVICES" = false ]; then
    print_error "Debe especificar al menos una opción de despliegue"
    show_help
    exit 1
fi

# Función para verificar dependencias
check_dependencies() {
    print_status "Verificando dependencias..."
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 no está instalado"
        exit 1
    fi
    
    # Verificar pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 no está instalado"
        exit 1
    fi
    
    # Verificar git
    if ! command -v git &> /dev/null; then
        print_error "git no está instalado"
        exit 1
    fi
    
    print_success "Dependencias verificadas"
}

# Función para crear backup
create_backup() {
    if [ "$CREATE_BACKUP" = true ]; then
        print_status "Creando backup de la base de datos..."
        
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup de la base de datos SQLite
        if [ -f "db.sqlite3" ]; then
            cp db.sqlite3 "$BACKUP_DIR/"
            print_success "Backup de base de datos creado en $BACKUP_DIR/"
        fi
        
        # Backup de archivos media
        if [ -d "media" ]; then
            tar -czf "$BACKUP_DIR/media_backup.tar.gz" media/
            print_success "Backup de archivos media creado en $BACKUP_DIR/"
        fi
        
        # Backup de archivos estáticos
        if [ -d "staticfiles" ]; then
            tar -czf "$BACKUP_DIR/staticfiles_backup.tar.gz" staticfiles/
            print_success "Backup de archivos estáticos creado en $BACKUP_DIR/"
        fi
        
        # Limpiar backups antiguos (mantener solo los últimos 5)
        find backups/ -type d -name "backup_*" | sort | head -n -5 | xargs rm -rf 2>/dev/null || true
        
        print_success "Backup completado exitosamente"
    fi
}

# Función para ejecutar migraciones
run_migrations() {
    if [ "$RUN_MIGRATIONS" = true ]; then
        print_status "Ejecutando migraciones de la base de datos..."
        
        # Verificar que el entorno virtual esté activado
        if [ -z "$VIRTUAL_ENV" ]; then
            print_warning "Entorno virtual no detectado, intentando activar..."
            if [ -f "venv/bin/activate" ]; then
                source venv/bin/activate
            elif [ -f ".venv/bin/activate" ]; then
                source .venv/bin/activate
            else
                print_error "No se pudo encontrar el entorno virtual"
                exit 1
            fi
        fi
        
        # Ejecutar migraciones
        python3 manage.py migrate --verbosity=2
        
        print_success "Migraciones ejecutadas exitosamente"
    fi
}

# Función para recolectar archivos estáticos
collect_static() {
    if [ "$COLLECT_STATIC" = true ]; then
        print_status "Recolectando archivos estáticos..."
        
        # Verificar que el entorno virtual esté activado
        if [ -z "$VIRTUAL_ENV" ]; then
            print_warning "Entorno virtual no detectado, intentando activar..."
            if [ -f "venv/bin/activate" ]; then
                source venv/bin/activate
            elif [ -f ".venv/bin/activate" ]; then
                source .venv/bin/activate
            else
                print_error "No se pudo encontrar el entorno virtual"
                exit 1
            fi
        fi
        
        # Crear directorio de archivos estáticos si no existe
        mkdir -p staticfiles
        
        # Recolectar archivos estáticos
        python3 manage.py collectstatic --noinput --verbosity=2
        
        print_success "Archivos estáticos recolectados exitosamente"
    fi
}

# Función para reiniciar servicios
restart_services() {
    if [ "$RESTART_SERVICES" = true ]; then
        print_status "Reiniciando servicios..."
        
        # Reiniciar servicios según el ambiente
        case $ENVIRONMENT in
            "production")
                # Reiniciar servicios de producción
                if command -v systemctl &> /dev/null; then
                    print_status "Reiniciando servicios con systemctl..."
                    sudo systemctl restart gestion-academica
                    sudo systemctl restart nginx
                elif command -v supervisorctl &> /dev/null; then
                    print_status "Reiniciando servicios con supervisor..."
                    sudo supervisorctl restart gestion-academica
                else
                    print_warning "No se detectó systemctl ni supervisor, reiniciando manualmente..."
                    # Aquí puedes agregar comandos específicos para tu servidor
                fi
                ;;
            "staging")
                # Reiniciar servicios de staging
                print_status "Reiniciando servicios de staging..."
                # Agregar comandos específicos para staging
                ;;
            *)
                print_error "Ambiente no reconocido: $ENVIRONMENT"
                exit 1
                ;;
        esac
        
        print_success "Servicios reiniciados exitosamente"
    fi
}

# Función para verificar el estado del despliegue
verify_deployment() {
    print_status "Verificando el estado del despliegue..."
    
    # Esperar un momento para que los servicios se estabilicen
    sleep 5
    
    # Verificar que Django esté funcionando
    if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        print_success "Django está funcionando correctamente"
    else
        print_warning "Django no responde en el puerto 8000"
    fi
    
    # Verificar que la API esté funcionando
    if curl -f http://localhost:8000/api/v1/ > /dev/null 2>&1; then
        print_success "API está funcionando correctamente"
    else
        print_warning "API no responde"
    fi
    
    # Verificar que los archivos estáticos estén disponibles
    if [ -d "staticfiles" ] && [ "$(ls -A staticfiles)" ]; then
        print_success "Archivos estáticos están disponibles"
    else
        print_warning "Archivos estáticos no están disponibles"
    fi
    
    print_success "Verificación del despliegue completada"
}

# Función principal
main() {
    print_status "Iniciando despliegue en ambiente: $ENVIRONMENT"
    print_status "Fecha y hora: $(date)"
    
    # Verificar dependencias
    check_dependencies
    
    # Crear backup si es necesario
    create_backup
    
    # Ejecutar migraciones si es necesario
    run_migrations
    
    # Recolectar archivos estáticos si es necesario
    collect_static
    
    # Reiniciar servicios si es necesario
    restart_services
    
    # Verificar el despliegue
    verify_deployment
    
    print_success "Despliegue completado exitosamente en $ENVIRONMENT"
    print_status "Fecha y hora de finalización: $(date)"
}

# Ejecutar función principal
main "$@"
