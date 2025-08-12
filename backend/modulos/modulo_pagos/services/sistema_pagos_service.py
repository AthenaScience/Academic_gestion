from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import (
    PlanPago, Cuota, 
    PagoCuota, Matricula, EstadoPagosEvento, InstitucionFinanciera
)
from modulos.modulo_certificados.models import Evento, Certificado
from modulos.modulo_estudiantes.models import Estudiante


class SistemaPagosService:
    """
    Servicio principal para manejar todo el sistema de pagos por cuotas
    """
    
    @classmethod
    def crear_plan_pago_estudiante(cls, estudiante, evento, numero_cuotas=None, monto_colegiatura=None):
        """
        Crea un plan de pago completo para un estudiante en un evento
        
        Args:
            estudiante: Instancia de Estudiante
            evento: Instancia de Evento
            numero_cuotas: Número de cuotas personalizado (opcional)
            monto_colegiatura: Monto total de colegiatura a prorratear (opcional)
        
        Returns:
            dict: Información del plan creado
        """
        try:
            with transaction.atomic():
                # Verificar si ya existe un plan para este estudiante
                if PlanPago.objects.filter(estudiante=estudiante, evento=evento).exists():
                    raise ValidationError("Ya existe un plan de pago para este estudiante en este evento")
                
                # Validar número de cuotas (requerido si no hay default)
                if numero_cuotas is None:
                    numero_cuotas = 1
                if numero_cuotas < 1:
                    raise ValidationError("El número de cuotas debe ser al menos 1")
                
                # Crear el plan de pago
                plan_pago = PlanPago.objects.create(
                    estudiante=estudiante,
                    evento=evento,
                    numero_cuotas=numero_cuotas,
                    monto_colegiatura=(monto_colegiatura if monto_colegiatura is not None else evento.costo_colegiatura),
                )
                
                # Generar las cuotas automáticamente
                cuotas_generadas = cls.generar_cuotas_plan(plan_pago)
                
                # Crear la matrícula
                matricula = Matricula.objects.create(
                    estudiante=estudiante,
                    evento=evento,
                    plan_pago=plan_pago,
                    estado='activa'
                )
                
                # Crear el estado de pagos del evento
                estado_pagos = EstadoPagosEvento.objects.create(
                    estudiante=estudiante,
                    evento=evento
                )
                
                return {
                    'plan_pago': plan_pago,
                    'cuotas_generadas': cuotas_generadas,
                    'matricula': matricula,
                    'estado_pagos': estado_pagos,
                    'resumen': cls.obtener_resumen_estudiante(estudiante, evento)
                }
                
        except Exception as e:
            raise ValidationError(f"Error al crear plan de pago: {str(e)}")
    
    @classmethod
    def generar_cuotas_plan(cls, plan_pago):
        """
        Genera automáticamente todas las cuotas para un plan de pago
        
        Args:
            plan_pago: Instancia de PlanPago
        
        Returns:
            list: Lista de cuotas generadas
        """
        cuotas = []
        evento = plan_pago.evento
        
        # Calcular monto por cuota
        monto_cuota = plan_pago.monto_colegiatura / plan_pago.numero_cuotas
        
        # Calcular fechas de vencimiento (mensuales desde la fecha de inicio del evento)
        fecha_inicio = evento.fecha_inicio
        
        for i in range(plan_pago.numero_cuotas):
            # Calcular fecha de vencimiento (cada mes)
            fecha_vencimiento = fecha_inicio + timedelta(days=30 * i)
            
            cuota = Cuota.objects.create(
                plan_pago=plan_pago,
                numero_cuota=i + 1,
                monto=monto_cuota,
                fecha_vencimiento=fecha_vencimiento,
                estado='pendiente'
            )
            cuotas.append(cuota)
        
        return cuotas
    
    @classmethod
    def registrar_pago_cuota(cls, cuota, monto_pagado, metodo_pago, 
                           institucion_financiera=None, codigo_comprobante=None,
                           observaciones=''):
        """
        Registra el pago de una cuota específica
        
        Args:
            cuota: Instancia de Cuota
            monto_pagado: Monto pagado
            metodo_pago: Método de pago
            institucion_financiera: Institución financiera (opcional)
            codigo_comprobante: Código del comprobante (opcional)
            observaciones: Observaciones adicionales
        
        Returns:
            PagoCuota: Instancia del pago registrado
        """
        try:
            with transaction.atomic():
                # Crear el registro de pago
                pago = PagoCuota.objects.create(
                    cuota=cuota,
                    monto_pagado=monto_pagado,
                    fecha_pago=date.today(),
                    metodo_pago=metodo_pago,
                    institucion_financiera=institucion_financiera,
                    codigo_comprobante=codigo_comprobante,
                    observaciones=observaciones
                )
                
                # Actualizar el estado de la cuota
                cuota.monto_pagado += monto_pagado
                
                # Si se pagó completamente, marcar como pagada
                if cuota.monto_pagado >= cuota.monto:
                    cuota.estado = 'pagado'
                    cuota.fecha_pago = date.today()
                
                cuota.save()
                
                # Actualizar el estado general de pagos del evento
                cls.actualizar_estado_pagos_evento(cuota.estudiante, cuota.evento)
                
                return pago
                
        except Exception as e:
            raise ValidationError(f"Error al registrar pago: {str(e)}")
    
    @classmethod
    def actualizar_estado_pagos_evento(cls, estudiante, evento):
        """
        Actualiza el estado general de pagos de un estudiante en un evento
        
        Args:
            estudiante: Instancia de Estudiante
            evento: Instancia de Evento
        """
        try:
            estado_pagos = EstadoPagosEvento.objects.get(estudiante=estudiante, evento=evento)
            
            # Obtener el plan de pago
            plan_pago = PlanPago.objects.get(estudiante=estudiante, evento=evento)
            
            # Verificar estado de matrícula
            matricula = Matricula.objects.get(estudiante=estudiante, evento=evento)
            estado_pagos.matricula_pagada = matricula.estado == 'activa'
            
            # Verificar estado de colegiatura
            cuotas_pendientes = Cuota.objects.filter(plan_pago=plan_pago, estado='pendiente').count()
            
            estado_pagos.colegiatura_al_dia = cuotas_pendientes == 0
            
            # Verificar estado de certificado
            certificado = evento.certificados.filter(estudiante=estudiante).first()
            if certificado:
                estado_pagos.certificado_pagado = certificado.pagado
            
            estado_pagos.save()
            
        except EstadoPagosEvento.DoesNotExist:
            pass
    
    @classmethod
    def obtener_resumen_estudiante(cls, estudiante, evento):
        """
        Obtiene un resumen completo del estado de pagos de un estudiante
        
        Args:
            estudiante: Instancia de Estudiante
            evento: Instancia de Evento
        
        Returns:
            dict: Resumen completo del estado de pagos
        """
        try:
            plan_pago = PlanPago.objects.get(estudiante=estudiante, evento=evento)
            cuotas = Cuota.objects.filter(plan_pago=plan_pago).order_by('numero_cuota')
            
            # Calcular estadísticas
            total_cuotas = cuotas.count()
            cuotas_pagadas = cuotas.filter(estado='pagado').count()
            cuotas_pendientes = cuotas.filter(estado='pendiente').count()
            cuotas_atrasadas = cuotas.filter(estado='atrasado').count()
            
            # Calcular montos
            monto_total = plan_pago.monto_colegiatura
            monto_pagado = sum(cuota.monto_pagado for cuota in cuotas)
            monto_pendiente = monto_total - monto_pagado
            
            # Calcular progreso
            progreso_porcentaje = (monto_pagado / monto_total * 100) if monto_total > 0 else 0
            
            # Obtener estado de matrícula y certificado
            matricula = Matricula.objects.get(estudiante=estudiante, evento=evento)
            certificado = Certificado.objects.filter(evento=evento, estudiante=estudiante).first()
            
            return {
                'estudiante': estudiante,
                'evento': evento,
                'plan_pago': plan_pago,
                'matricula': {
                    'estado': matricula.estado,
                    'pagada': matricula.estado == 'activa'
                },
                'colegiatura': {
                    'monto_total': monto_total,
                    'monto_pagado': monto_pagado,
                    'monto_pendiente': monto_pendiente,
                    'progreso_porcentaje': round(progreso_porcentaje, 2),
                    'cuotas': {
                        'total': total_cuotas,
                        'pagadas': cuotas_pagadas,
                        'pendientes': cuotas_pendientes,
                        'atrasadas': cuotas_atrasadas
                    }
                },
                'certificado': {
                    'pagado': certificado.pagado if certificado else False,
                    'monto': evento.costo_certificado
                },
                'estado_general': cls.calcular_estado_general(cuotas_pagadas, cuotas_atrasadas, total_cuotas)
            }
            
        except PlanPago.DoesNotExist:
            return None
    
    @classmethod
    def calcular_estado_general(cls, cuotas_pagadas, cuotas_atrasadas, total_cuotas):
        """
        Calcula el estado general del estudiante basado en sus cuotas
        
        Args:
            cuotas_pagadas: Número de cuotas pagadas
            cuotas_atrasadas: Número de cuotas atrasadas
            total_cuotas: Total de cuotas
        
        Returns:
            str: Estado general
        """
        if cuotas_pagadas == total_cuotas:
            return 'completado'
        elif cuotas_atrasadas > 0:
            return 'atrasado'
        elif cuotas_pagadas > 0:
            return 'al_dia'
        else:
            return 'pendiente'
    
    @classmethod
    def verificar_cuotas_atrasadas(cls):
        """
        Verifica y actualiza el estado de las cuotas atrasadas
        
        Returns:
            list: Lista de cuotas atrasadas
        """
        cuotas_atrasadas = []
        fecha_actual = date.today()
        
        # Buscar cuotas pendientes que han vencido
        cuotas_vencidas = Cuota.objects.filter(
            estado='pendiente',
            fecha_vencimiento__lt=fecha_actual
        )
        
        for cuota in cuotas_vencidas:
            cuota.estado = 'atrasado'
            cuota.save()
            cuotas_atrasadas.append(cuota)
            
            # Actualizar estado del evento
            cls.actualizar_estado_pagos_evento(cuota.estudiante, cuota.evento)
        
        return cuotas_atrasadas
    
    @classmethod
    def obtener_estudiantes_atrasados(cls, evento=None):
        """
        Obtiene la lista de estudiantes atrasados en sus pagos
        
        Args:
            evento: Evento específico (opcional)
        
        Returns:
            list: Lista de estudiantes atrasados
        """
        filtro = {'estado': 'atrasado'}
        if evento:
            filtro['plan_pago__evento'] = evento
        
        cuotas_atrasadas = Cuota.objects.filter(**filtro).select_related(
            'plan_pago__estudiante',
            'plan_pago__evento'
        )
        
        estudiantes_atrasados = []
        for cuota in cuotas_atrasadas:
            estudiante = cuota.plan_pago.estudiante
            evento = cuota.plan_pago.evento
            
            if not any(e['estudiante_id'] == estudiante.id and e['evento_id'] == evento.id 
                      for e in estudiantes_atrasados):
                estudiantes_atrasados.append({
                    'estudiante_id': estudiante.id,
                    'estudiante_nombre': f"{estudiante.nombres} {estudiante.apellidos}",
                    'evento_id': evento.id,
                    'evento_nombre': evento.nombre,
                    'cuotas_atrasadas': cuotas_atrasadas.filter(
                        plan_pago__estudiante=estudiante,
                        plan_pago__evento=evento,
                        estado='atrasado'
                    ).count(),
                    'dias_atraso': (date.today() - cuota.fecha_vencimiento).days
                })
        
        return estudiantes_atrasados
    
    @classmethod
    def obtener_estadisticas_evento(cls, evento):
        """
        Obtiene estadísticas completas de pagos para un evento
        
        Args:
            evento: Instancia de Evento
        
        Returns:
            dict: Estadísticas del evento
        """
        try:
            # Obtener todos los planes de pago del evento
            planes_pago = PlanPago.objects.filter(evento=evento)
            
            total_estudiantes = planes_pago.count()
            total_cuotas = sum(plan.numero_cuotas for plan in planes_pago)
            
            # Contar cuotas por estado
            cuotas_pagadas = Cuota.objects.filter(plan_pago__evento=evento, estado='pagado').count()
            
            cuotas_pendientes = Cuota.objects.filter(plan_pago__evento=evento, estado='pendiente').count()
            
            cuotas_atrasadas = Cuota.objects.filter(plan_pago__evento=evento, estado='atrasado').count()
            
            # Calcular montos
            monto_total_colegiatura = sum(plan.monto_colegiatura for plan in planes_pago)
            monto_total_pagado = sum(
                cuota.monto_pagado for cuota in Cuota.objects.filter(plan_pago__evento=evento)
            )
            
            return {
                'evento': evento,
                'estudiantes': {
                    'total': total_estudiantes,
                    'matriculados': total_estudiantes
                },
                'cuotas': {
                    'total': total_cuotas,
                    'pagadas': cuotas_pagadas,
                    'pendientes': cuotas_pendientes,
                    'atrasadas': cuotas_atrasadas
                },
                'montos': {
                    'total_colegiatura': monto_total_colegiatura,
                    'total_pagado': monto_total_pagado,
                    'total_pendiente': monto_total_colegiatura - monto_total_pagado,
                    'progreso_porcentaje': round((monto_total_pagado / monto_total_colegiatura * 100) if monto_total_colegiatura > 0 else 0, 2)
                },
                'estudiantes_atrasados': cls.obtener_estudiantes_atrasados(evento)
            }
            
        except Exception as e:
            return None
