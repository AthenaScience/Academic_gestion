from __future__ import annotations

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento
from .models import Matricula, PlanPago, EstadoPagosEvento
from .services.sistema_pagos_service import SistemaPagosService


@receiver(m2m_changed, sender=Estudiante.eventos_matriculados.through)
def crear_plan_pago_al_agregar_evento(sender, instance: Estudiante, action, reverse, pk_set, **kwargs):
    """
    Cuando se agrega un evento a `estudiante.eventos_matriculados` desde el admin o API,
    crear automáticamente un PlanPagoColegiatura estándar, cuotas, matrícula y estado de pagos.
    """
    if action != "post_add" or reverse:
        return

    if not pk_set:
        return

    for evento_pk in pk_set:
        try:
            evento = Evento.objects.get(pk=evento_pk)
        except Evento.DoesNotExist:
            continue

        # Si ya existe plan, no duplicar
        if PlanPago.objects.filter(estudiante=instance, evento=evento).exists():
            # Asegurar estado de pagos
            EstadoPagosEvento.objects.get_or_create(estudiante=instance, evento=evento)
            continue

        try:
            SistemaPagosService.crear_plan_pago_estudiante(
                estudiante=instance,
                evento=evento,
            )
        except Exception:
            # Evitar que una excepción bloquee el guardado en admin/API
            # (ya hay validaciones en el servicio)
            pass


@receiver(post_save, sender=Matricula)
def asegurar_plan_y_cuotas_en_matricula(sender, instance: Matricula, created, **kwargs):
    """
    Al crear una `Matricula`, si no tiene plan_pago asociado, crear uno estándar con las cuotas.
    """
    if not created:
        return

    if instance.plan_pago:
        return

    estudiante = instance.estudiante
    evento = instance.evento
    if not estudiante or not evento:
        return

    # Crear plan si no existe y asociarlo a la matrícula
    plan = PlanPago.objects.filter(estudiante=estudiante, evento=evento).first()
    if not plan:
        try:
            result = SistemaPagosService.crear_plan_pago_estudiante(
                estudiante=estudiante, evento=evento
            )
            plan = result.get("plan_pago")
        except Exception:
            plan = None

    if plan and not instance.plan_pago:
        instance.plan_pago = plan
        instance.save(update_fields=["plan_pago"]) 


