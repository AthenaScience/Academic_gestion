from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento
from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService


class Command(BaseCommand):
    help = 'Crea un plan de pago para un estudiante en un evento específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--estudiante_id',
            type=int,
            help='ID del estudiante',
            required=True
        )
        parser.add_argument(
            '--evento_id',
            type=int,
            help='ID del evento',
            required=True
        )
        parser.add_argument(
            '--numero_cuotas',
            type=int,
            help='Número de cuotas personalizado (opcional)',
            required=False
        )

    def handle(self, *args, **options):
        try:
            # Obtener estudiante y evento
            estudiante = Estudiante.objects.get(id=options['estudiante_id'])
            evento = Evento.objects.get(id=options['evento_id'])
            
            self.stdout.write(
                self.style.SUCCESS(f'Creando plan de pago para {estudiante} en {evento}')
            )
            
            # Crear el plan de pago usando el servicio
            resultado = SistemaPagosService.crear_plan_pago_estudiante(
                estudiante=estudiante,
                evento=evento,
                numero_cuotas=options.get('numero_cuotas')
            )
            
            # Mostrar resumen
            self.stdout.write(
                self.style.SUCCESS('✅ Plan de pago creado exitosamente')
            )
            
            resumen = resultado['resumen']
            self.stdout.write(f"""
📊 RESUMEN DEL PLAN DE PAGO:
============================
👤 Estudiante: {resumen['estudiante']}
📚 Evento: {resumen['evento']}
💰 Monto Total Colegiatura: ${resumen['colegiatura']['monto_total']}
📅 Número de Cuotas: {resumen['colegiatura']['cuotas']['total']}
📈 Progreso: {resumen['colegiatura']['progreso_porcentaje']}%
🎯 Estado General: {resumen['estado_general'].upper()}
            """)
            
        except Estudiante.DoesNotExist:
            raise CommandError(f'No existe un estudiante con ID {options["estudiante_id"]}')
        except Evento.DoesNotExist:
            raise CommandError(f'No existe un evento con ID {options["evento_id"]}')
        except Exception as e:
            raise CommandError(f'Error al crear plan de pago: {str(e)}')
