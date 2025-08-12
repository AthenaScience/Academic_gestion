from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from modulos.modulo_pagos.models import Cuota, InstitucionFinanciera
from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService


class Command(BaseCommand):
    help = 'Registra el pago de una cuota específica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cuota_id',
            type=int,
            help='ID de la cuota a pagar',
            required=True
        )
        parser.add_argument(
            '--monto_pagado',
            type=float,
            help='Monto pagado',
            required=True
        )
        parser.add_argument(
            '--metodo_pago',
            type=str,
            choices=['efectivo', 'transferencia', 'tarjeta', 'cheque', 'deposito', 'pago_movil'],
            help='Método de pago',
            required=True
        )
        parser.add_argument(
            '--institucion_financiera_id',
            type=int,
            help='ID de la institución financiera (opcional)',
            required=False
        )
        parser.add_argument(
            '--codigo_comprobante',
            type=str,
            help='Código del comprobante (opcional)',
            required=False
        )
        parser.add_argument(
            '--observaciones',
            type=str,
            help='Observaciones adicionales (opcional)',
            required=False
        )

    def handle(self, *args, **options):
        try:
            # Obtener la cuota
            cuota = Cuota.objects.get(id=options['cuota_id'])
            
            self.stdout.write(
                self.style.SUCCESS(f'Registrando pago de cuota {cuota.numero_cuota} para {cuota.estudiante}')
            )
            
            # Obtener institución financiera si se especifica
            institucion_financiera = None
            if options.get('institucion_financiera_id'):
                institucion_financiera = InstitucionFinanciera.objects.get(
                    id=options['institucion_financiera_id']
                )
            
            # Registrar el pago usando el servicio
            pago = SistemaPagosService.registrar_pago_cuota(
                cuota=cuota,
                monto_pagado=options['monto_pagado'],
                metodo_pago=options['metodo_pago'],
                institucion_financiera=institucion_financiera,
                codigo_comprobante=options.get('codigo_comprobante'),
                observaciones=options.get('observaciones', '')
            )
            
            # Mostrar resumen del pago
            self.stdout.write(
                self.style.SUCCESS('✅ Pago registrado exitosamente')
            )
            
            self.stdout.write(f"""
💰 RESUMEN DEL PAGO:
====================
📅 Fecha: {pago.fecha_pago}
💵 Monto Pagado: ${pago.monto_pagado}
💳 Método: {pago.metodo_pago}
🏦 Institución: {pago.institucion_financiera or 'No especificada'}
📋 Comprobante: {pago.codigo_comprobante or 'No especificado'}
📝 Observaciones: {pago.observaciones or 'Ninguna'}
            """)
            
            # Mostrar estado actual de la cuota
            self.stdout.write(f"""
📊 ESTADO ACTUAL DE LA CUOTA:
==============================
🔢 Número: {cuota.numero_cuota}
💰 Monto Total: ${cuota.monto}
💵 Monto Pagado: ${cuota.monto_pagado}
📊 Estado: {cuota.estado.upper()}
📅 Vencimiento: {cuota.fecha_vencimiento}
            """)
            
        except Cuota.DoesNotExist:
            raise CommandError(f'No existe una cuota con ID {options["cuota_id"]}')
        except InstitucionFinanciera.DoesNotExist:
            raise CommandError(f'No existe una institución financiera con ID {options["institucion_financiera_id"]}')
        except Exception as e:
            raise CommandError(f'Error al registrar pago: {str(e)}')
