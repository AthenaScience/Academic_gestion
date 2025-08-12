"""
Configuración de logging estructurado para Gestion Academica
============================================================

Este módulo proporciona:
- Logging estructurado con formato JSON
- Rotación de archivos de log
- Diferentes niveles por ambiente
- Métricas y monitoreo integrado
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

# Configuración base del logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Directorios de logs
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# Archivos de log
LOG_FILES = {
    'django': LOG_DIR / 'django.log',
    'application': LOG_DIR / 'application.log',
    'security': LOG_DIR / 'security.log',
    'performance': LOG_DIR / 'performance.log',
    'errors': LOG_DIR / 'errors.log',
    'access': LOG_DIR / 'access.log',
}


class StructuredFormatter(logging.Formatter):
    """
    Formateador de logs estructurado en JSON
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro de log como JSON estructurado"""
        
        # Datos base del log
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Agregar excepción si existe
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Agregar campos extra si existen
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Agregar contexto de request si está disponible
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        # Agregar métricas de rendimiento si están disponibles
        if hasattr(record, 'execution_time'):
            log_data['execution_time_ms'] = record.execution_time
        
        if hasattr(record, 'memory_usage'):
            log_data['memory_usage_mb'] = record.memory_usage
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class PerformanceFilter(logging.Filter):
    """
    Filtro para logs de rendimiento
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filtra logs basándose en criterios de rendimiento"""
        return (
            hasattr(record, 'execution_time') or
            hasattr(record, 'memory_usage') or
            'performance' in record.name.lower() or
            'slow' in record.getMessage().lower()
        )


class SecurityFilter(logging.Filter):
    """
    Filtro para logs de seguridad
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filtra logs basándose en criterios de seguridad"""
        security_keywords = [
            'login', 'logout', 'authentication', 'authorization',
            'permission', 'access', 'security', 'attack', 'breach',
            'password', 'token', 'session', 'csrf', 'xss', 'sql'
        ]
        
        message_lower = record.getMessage().lower()
        return any(keyword in message_lower for keyword in security_keywords)


def setup_logging(debug: bool = False) -> None:
    """
    Configura el sistema de logging completo
    
    Args:
        debug: Si está en modo debug
    """
    
    # Nivel de log basado en debug
    level = logging.DEBUG if debug else logging.INFO
    
    # Configurar logging root
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[]
    )
    
    # Configurar handlers para diferentes tipos de logs
    setup_django_logging(level)
    setup_application_logging(level)
    setup_security_logging(level)
    setup_performance_logging(level)
    setup_error_logging(level)
    setup_access_logging(level)
    
    # Configurar logging de terceros
    setup_third_party_logging(level)


def setup_django_logging(level: int) -> None:
    """Configura logging específico de Django"""
    
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILES['django'],
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('django')
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False


def setup_application_logging(level: int) -> None:
    """Configura logging de la aplicación"""
    
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILES['application'],
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('modulos')
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False


def setup_security_logging(level: int) -> None:
    """Configura logging de seguridad"""
    
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILES['security'],
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10,  # Más backups para seguridad
        encoding='utf-8'
    )
    
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    # Aplicar filtro de seguridad
    handler.addFilter(SecurityFilter())
    
    logger = logging.getLogger('security')
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False


def setup_performance_logging(level: int) -> None:
    """Configura logging de rendimiento"""
    
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILES['performance'],
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    # Aplicar filtro de rendimiento
    handler.addFilter(PerformanceFilter())
    
    logger = logging.getLogger('performance')
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False


def setup_error_logging(level: int) -> None:
    """Configura logging de errores"""
    
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILES['errors'],
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    # Solo errores y críticos
    handler.setLevel(logging.ERROR)
    
    logger = logging.getLogger('errors')
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    logger.propagate = False


def setup_access_logging(level: int) -> None:
    """Configura logging de acceso"""
    
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILES['access'],
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    logger = logging.getLogger('access')
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False


def setup_third_party_logging(level: int) -> None:
    """Configura logging de librerías de terceros"""
    
    # Reducir verbosidad de librerías externas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)


# Funciones de utilidad para logging estructurado
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    extra_fields: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None:
    """
    Función de utilidad para logging con contexto adicional
    
    Args:
        logger: Logger a usar
        level: Nivel de log
        message: Mensaje del log
        extra_fields: Campos extra para el log
        **kwargs: Campos adicionales como request_id, user_id, etc.
    """
    
    if extra_fields is None:
        extra_fields = {}
    
    # Agregar campos del contexto
    for key, value in kwargs.items():
        if value is not None:
            extra_fields[key] = value
    
    # Crear registro con campos extra
    record = logger.makeRecord(
        logger.name, level, __file__, 0, message, (), None
    )
    record.extra_fields = extra_fields
    
    logger.handle(record)


def log_performance(
    logger: logging.Logger,
    operation: str,
    execution_time: float,
    memory_usage: Optional[float] = None,
    **kwargs
) -> None:
    """
    Función específica para logging de rendimiento
    
    Args:
        logger: Logger a usar
        operation: Nombre de la operación
        execution_time: Tiempo de ejecución en segundos
        memory_usage: Uso de memoria en MB
        **kwargs: Campos adicionales
    """
    
    extra_fields = {
        'operation': operation,
        'execution_time': execution_time * 1000,  # Convertir a ms
        'memory_usage': memory_usage,
        'log_type': 'performance'
    }
    
    if execution_time > 1.0:  # Log lento si toma más de 1 segundo
        level = logging.WARNING
        extra_fields['performance_issue'] = 'slow_operation'
    else:
        level = logging.INFO
    
    log_with_context(logger, level, f"Performance: {operation}", extra_fields, **kwargs)


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    description: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **kwargs
) -> None:
    """
    Función específica para logging de eventos de seguridad
    
    Args:
        logger: Logger a usar
        event_type: Tipo de evento de seguridad
        description: Descripción del evento
        user_id: ID del usuario involucrado
        ip_address: Dirección IP
        **kwargs: Campos adicionales
    """
    
    extra_fields = {
        'event_type': event_type,
        'description': description,
        'log_type': 'security'
    }
    
    log_with_context(
        logger,
        logging.INFO,
        f"Security Event: {event_type}",
        extra_fields,
        user_id=user_id,
        ip_address=ip_address,
        **kwargs
    )


# Configuración automática al importar el módulo
if __name__ == '__main__':
    setup_logging(debug=True)
    logger = logging.getLogger('test')
    
    # Ejemplo de uso
    log_with_context(
        logger,
        logging.INFO,
        "Test message",
        extra_fields={'test_field': 'test_value'},
        request_id='req-123',
        user_id='user-456'
    )
    
    log_performance(
        logger,
        "database_query",
        0.5,
        memory_usage=25.5,
        request_id='req-123'
    )
    
    log_security_event(
        logger,
        "login_attempt",
        "Successful login",
        user_id='user-456',
        ip_address='192.168.1.1'
    )
