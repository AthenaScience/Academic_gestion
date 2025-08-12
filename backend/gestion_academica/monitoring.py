"""
Sistema de Métricas y Monitoreo para Gestion Academica
======================================================

Este módulo proporciona:
- Métricas de rendimiento de la aplicación
- Monitoreo de base de datos
- Métricas de negocio
- Health checks
- Alertas y notificaciones
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import logging

# Configurar logger
logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Punto de métrica con timestamp y valor"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Métrica con nombre, tipo y valores históricos"""
    name: str
    metric_type: str  # 'counter', 'gauge', 'histogram'
    description: str
    unit: str
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Colector de métricas del sistema"""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.lock = threading.Lock()
        self.start_time = datetime.now()
        
        # Métricas del sistema
        self._init_system_metrics()
        
        # Iniciar recolección automática
        self._start_collection()
    
    def _init_system_metrics(self):
        """Inicializa métricas básicas del sistema"""
        
        # Métricas de CPU
        self.register_metric(
            'system.cpu.usage',
            'gauge',
            'CPU usage percentage',
            'percent'
        )
        
        # Métricas de memoria
        self.register_metric(
            'system.memory.usage',
            'gauge',
            'Memory usage percentage',
            'percent'
        )
        
        # Métricas de disco
        self.register_metric(
            'system.disk.usage',
            'gauge',
            'Disk usage percentage',
            'percent'
        )
        
        # Métricas de red
        self.register_metric(
            'system.network.bytes_sent',
            'counter',
            'Network bytes sent',
            'bytes'
        )
        
        self.register_metric(
            'system.network.bytes_recv',
            'counter',
            'Network bytes received',
            'bytes'
        )
        
        # Métricas de la aplicación
        self.register_metric(
            'app.requests.total',
            'counter',
            'Total HTTP requests',
            'requests'
        )
        
        self.register_metric(
            'app.requests.duration',
            'histogram',
            'HTTP request duration',
            'milliseconds'
        )
        
        self.register_metric(
            'app.errors.total',
            'counter',
            'Total application errors',
            'errors'
        )
        
        # Métricas de base de datos
        self.register_metric(
            'db.queries.total',
            'counter',
            'Total database queries',
            'queries'
        )
        
        self.register_metric(
            'db.queries.duration',
            'histogram',
            'Database query duration',
            'milliseconds'
        )
        
        # Métricas de negocio
        self.register_metric(
            'business.students.total',
            'gauge',
            'Total number of students',
            'students'
        )
        
        self.register_metric(
            'business.certificates.issued',
            'counter',
            'Total certificates issued',
            'certificates'
        )
        
        self.register_metric(
            'business.payments.total',
            'counter',
            'Total payments processed',
            'payments'
        )
    
    def register_metric(self, name: str, metric_type: str, description: str, unit: str, tags: Optional[Dict[str, str]] = None):
        """Registra una nueva métrica"""
        with self.lock:
            self.metrics[name] = Metric(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                tags=tags or {}
            )
    
    def record_value(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Registra un valor para una métrica"""
        if metric_name not in self.metrics:
            logger.warning(f"Métrica no registrada: {metric_name}")
            return
        
        with self.lock:
            metric = self.metrics[metric_name]
            point = MetricPoint(
                timestamp=datetime.now(),
                value=value,
                tags=tags or {}
            )
            metric.values.append(point)
    
    def increment_counter(self, metric_name: str, increment: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Incrementa un contador"""
        if metric_name not in self.metrics:
            logger.warning(f"Métrica no registrada: {metric_name}")
            return
        
        with self.lock:
            metric = self.metrics[metric_name]
            if metric.metric_type == 'counter':
                # Para contadores, sumamos al último valor o iniciamos en 0
                if metric.values:
                    last_value = metric.values[-1].value
                    new_value = last_value + increment
                else:
                    new_value = increment
                
                point = MetricPoint(
                    timestamp=datetime.now(),
                    value=new_value,
                    tags=tags or {}
                )
                metric.values.append(point)
    
    def get_metric_value(self, metric_name: str) -> Optional[float]:
        """Obtiene el valor actual de una métrica"""
        if metric_name not in self.metrics:
            return None
        
        with self.lock:
            metric = self.metrics[metric_name]
            if metric.values:
                return metric.values[-1].value
            return None
    
    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[MetricPoint]:
        """Obtiene el historial de una métrica"""
        if metric_name not in self.metrics:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            metric = self.metrics[metric_name]
            return [
                point for point in metric.values
                if point.timestamp >= cutoff_time
            ]
    
    def _start_collection(self):
        """Inicia la recolección automática de métricas del sistema"""
        def collect_system_metrics():
            while True:
                try:
                    # CPU
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.record_value('system.cpu.usage', cpu_percent)
                    
                    # Memoria
                    memory = psutil.virtual_memory()
                    self.record_value('system.memory.usage', memory.percent)
                    
                    # Disco
                    disk = psutil.disk_usage('/')
                    self.record_value('system.disk.usage', disk.percent)
                    
                    # Red
                    net_io = psutil.net_io_counters()
                    self.record_value('system.network.bytes_sent', net_io.bytes_sent)
                    self.record_value('system.network.bytes_recv', net_io.bytes_recv)
                    
                    time.sleep(60)  # Recolectar cada minuto
                    
                except Exception as e:
                    logger.error(f"Error recolectando métricas del sistema: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()


class HealthChecker:
    """Verificador de salud del sistema"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.health_checks: List[Callable] = []
        self._init_health_checks()
    
    def _init_health_checks(self):
        """Inicializa los health checks"""
        
        # Health check de CPU
        def check_cpu():
            cpu_usage = self.metrics.get_metric_value('system.cpu.usage')
            if cpu_usage and cpu_usage > 90:
                return False, f"CPU usage too high: {cpu_usage}%"
            return True, "CPU usage OK"
        
        # Health check de memoria
        def check_memory():
            memory_usage = self.metrics.get_metric_value('system.memory.usage')
            if memory_usage and memory_usage > 95:
                return False, f"Memory usage too high: {memory_usage}%"
            return True, "Memory usage OK"
        
        # Health check de disco
        def check_disk():
            disk_usage = self.metrics.get_metric_value('system.disk.usage')
            if disk_usage and disk_usage > 90:
                return False, f"Disk usage too high: {disk_usage}%"
            return True, "Disk usage OK"
        
        # Health check de errores de aplicación
        def check_app_errors():
            error_rate = self._calculate_error_rate()
            if error_rate > 0.05:  # Más del 5% de errores
                return False, f"Error rate too high: {error_rate:.2%}"
            return True, "Error rate OK"
        
        self.health_checks = [check_cpu, check_memory, check_disk, check_app_errors]
    
    def _calculate_error_rate(self) -> float:
        """Calcula la tasa de errores"""
        total_requests = self.metrics.get_metric_value('app.requests.total') or 0
        total_errors = self.metrics.get_metric_value('app.errors.total') or 0
        
        if total_requests == 0:
            return 0.0
        
        return total_errors / total_requests
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Ejecuta todos los health checks"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        failed_checks = 0
        
        for check in self.health_checks:
            try:
                is_healthy, message = check()
                check_name = check.__name__
                
                results['checks'][check_name] = {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'message': message
                }
                
                if not is_healthy:
                    failed_checks += 1
                    
            except Exception as e:
                results['checks'][check.__name__] = {
                    'status': 'error',
                    'message': f"Health check failed: {str(e)}"
                }
                failed_checks += 1
        
        # Determinar estado general
        if failed_checks > 0:
            results['overall_status'] = 'unhealthy'
        
        return results


class PerformanceMonitor:
    """Monitor de rendimiento de la aplicación"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.active_operations: Dict[str, float] = {}
    
    def start_operation(self, operation_name: str):
        """Inicia el monitoreo de una operación"""
        self.active_operations[operation_name] = time.time()
    
    def end_operation(self, operation_name: str, success: bool = True):
        """Termina el monitoreo de una operación"""
        if operation_name not in self.active_operations:
            return
        
        start_time = self.active_operations.pop(operation_name)
        duration = time.time() - start_time
        
        # Registrar duración
        self.metrics.record_value(
            'app.requests.duration',
            duration * 1000,  # Convertir a milisegundos
            tags={'operation': operation_name, 'success': str(success)}
        )
        
        # Incrementar contador de requests
        self.metrics.increment_counter('app.requests.total')
        
        # Incrementar contador de errores si falló
        if not success:
            self.metrics.increment_counter('app.errors.total')
        
        # Log de operaciones lentas
        if duration > 1.0:  # Más de 1 segundo
            logger.warning(f"Operación lenta detectada: {operation_name} tomó {duration:.2f}s")
    
    def monitor_database_query(self, query_name: str):
        """Decorador para monitorear consultas de base de datos"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    
                    # Registrar métricas de base de datos
                    self.metrics.record_value(
                        'db.queries.duration',
                        duration * 1000,
                        tags={'query': query_name, 'success': str(success)}
                    )
                    
                    self.metrics.increment_counter('db.queries.total')
            
            return wrapper
        return decorator


class BusinessMetricsCollector:
    """Colector de métricas de negocio"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    def update_student_count(self, count: int):
        """Actualiza el conteo de estudiantes"""
        self.metrics.record_value('business.students.total', count)
    
    def increment_certificates_issued(self, count: int = 1):
        """Incrementa el contador de certificados emitidos"""
        self.metrics.increment_counter('business.certificates.issued', count)
    
    def increment_payments_processed(self, count: int = 1):
        """Incrementa el contador de pagos procesados"""
        self.metrics.increment_counter('business.payments.total', count)


class MetricsExporter:
    """Exportador de métricas para sistemas de monitoreo externos"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    def export_prometheus_format(self) -> str:
        """Exporta métricas en formato Prometheus"""
        lines = []
        
        with self.metrics.lock:
            for metric_name, metric in self.metrics.metrics.items():
                if not metric.values:
                    continue
                
                current_value = metric.values[-1].value
                
                # Construir etiquetas
                tags_str = ""
                if metric.tags:
                    tag_pairs = [f'{k}="{v}"' for k, v in metric.tags.items()]
                    tags_str = "{" + ",".join(tag_pairs) + "}"
                
                # Formato Prometheus
                if metric.metric_type == 'counter':
                    lines.append(f'{metric_name}_total{tags_str} {current_value}')
                elif metric.metric_type == 'gauge':
                    lines.append(f'{metric_name}{tags_str} {current_value}')
                elif metric.metric_type == 'histogram':
                    # Para histogramas, exportar buckets
                    lines.append(f'{metric_name}_sum{tags_str} {current_value}')
                    lines.append(f'{metric_name}_count{tags_str} {len(metric.values)}')
        
        return "\n".join(lines)
    
    def export_json_format(self) -> str:
        """Exporta métricas en formato JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {}
        }
        
        with self.metrics.lock:
            for metric_name, metric in self.metrics.metrics.items():
                if not metric.values:
                    continue
                
                current_value = metric.values[-1].value
                
                data['metrics'][metric_name] = {
                    'type': metric.metric_type,
                    'description': metric.description,
                    'unit': metric.unit,
                    'current_value': current_value,
                    'tags': metric.tags,
                    'last_updated': metric.values[-1].timestamp.isoformat()
                }
        
        return json.dumps(data, indent=2, default=str)


# Instancia global del colector de métricas
metrics_collector = MetricsCollector()
health_checker = HealthChecker(metrics_collector)
performance_monitor = PerformanceMonitor(metrics_collector)
business_metrics = BusinessMetricsCollector(metrics_collector)
metrics_exporter = MetricsExporter(metrics_collector)


# Funciones de utilidad para uso en la aplicación
def track_request_duration(operation_name: str):
    """Decorador para trackear duración de requests"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            performance_monitor.start_operation(operation_name)
            try:
                result = func(*args, **kwargs)
                performance_monitor.end_operation(operation_name, success=True)
                return result
            except Exception as e:
                performance_monitor.end_operation(operation_name, success=False)
                raise
        return wrapper
    return decorator


def track_database_query(query_name: str):
    """Decorador para trackear consultas de base de datos"""
    return performance_monitor.monitor_database_query(query_name)


def get_system_health() -> Dict[str, Any]:
    """Obtiene el estado de salud del sistema"""
    return health_checker.run_health_checks()


def get_metrics_summary() -> Dict[str, Any]:
    """Obtiene un resumen de las métricas principales"""
    summary = {
        'system': {
            'cpu_usage': metrics_collector.get_metric_value('system.cpu.usage'),
            'memory_usage': metrics_collector.get_metric_value('system.memory.usage'),
            'disk_usage': metrics_collector.get_metric_value('system.disk.usage'),
        },
        'application': {
            'total_requests': metrics_collector.get_metric_value('app.requests.total'),
            'error_rate': health_checker._calculate_error_rate(),
        },
        'business': {
            'total_students': metrics_collector.get_metric_value('business.students.total'),
            'certificates_issued': metrics_collector.get_metric_value('business.certificates.issued'),
            'payments_processed': metrics_collector.get_metric_value('business.payments.total'),
        }
    }
    
    return summary


# Ejemplo de uso
if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Ejemplo de uso de métricas
    @track_request_duration('test_operation')
    def test_function():
        time.sleep(0.1)
        return "success"
    
    # Ejecutar función de prueba
    result = test_function()
    
    # Obtener métricas
    summary = get_metrics_summary()
    print("Resumen de métricas:", json.dumps(summary, indent=2, default=str))
    
    # Exportar en formato Prometheus
    prometheus_metrics = metrics_exporter.export_prometheus_format()
    print("\nMétricas Prometheus:")
    print(prometheus_metrics)
