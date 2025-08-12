from django.core.management.base import BaseCommand, CommandError
from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento
from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService
from django.utils import timezone


class Command(BaseCommand):
    help = 'Muestra el resumen completo de pagos de un estudiante en un evento'

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

    def handle(self, *args, **options):
        try:
            # Obtener estudiante y evento
            estudiante = Estudiante.objects.get(id=options['estudiante_id'])
            evento = Evento.objects.get(id=options['evento_id'])
            
            self.stdout.write(
                self.style.SUCCESS(f'📊 Generando resumen para {estudiante} en {evento}')
            )
            
            # Obtener el resumen usando el servicio
            resumen = SistemaPagosService.obtener_resumen_estudiante(estudiante, evento)
            
            if not resumen:
                self.stdout.write(
                    self.style.WARNING('⚠️  No se encontró un plan de pago para este estudiante en este evento')
                )
                return
            
            # Mostrar resumen completo
            self.stdout.write(f"""
🎓 RESUMEN COMPLETO DE PAGOS
============================
👤 ESTUDIANTE: {resumen['estudiante']}
📚 EVENTO: {resumen['evento']}
📅 FECHA: {timezone.now().strftime('%d/%m/%Y %H:%M')}

💰 MATRÍCULA:
   • Estado: {resumen['matricula']['estado'].upper()}
   • Pagada: {'✅ SÍ' if resumen['matricula']['pagada'] else '❌ NO'}
   • Monto: ${evento.costo_matricula}

📊 COLEGIATURA:
   • Monto Total: ${resumen['colegiatura']['monto_total']}
   • Monto Pagado: ${resumen['colegiatura']['monto_pagado']}
   • Monto Pendiente: ${resumen['colegiatura']['monto_pendiente']}
   • Progreso: {resumen['colegiatura']['progreso_porcentaje']}%

📅 CUOTAS:
   • Total: {resumen['colegiatura']['cuotas']['total']}
   • Pagadas: {resumen['colegiatura']['cuotas']['pagadas']} ✅
   • Pendientes: {resumen['colegiatura']['cuotas']['pendientes']} ⏳
   • Atrasadas: {resumen['colegiatura']['cuotas']['atrasadas']} ⚠️

🎓 CERTIFICADO:
   • Estado: {'✅ PAGADO' if resumen['certificado']['pagado'] else '❌ PENDIENTE'}
   • Monto: ${resumen['certificado']['monto']}

🎯 ESTADO GENERAL: {resumen['estado_general'].upper()}
            """)
            
            # Mostrar detalles de las cuotas si existen
            if resumen['colegiatura']['cuotas']['total'] > 0:
                self.stdout.write('\n📋 DETALLE DE CUOTAS:')
                self.stdout.write('=' * 30)
                
                # Obtener las cuotas del plan de pago
                cuotas = resumen['plan_pago'].cuotas.all().order_by('numero_cuota')
                
                for cuota in cuotas:
                    estado_icono = {
                        'pagado': '✅',
                        'pendiente': '⏳',
                        'atrasado': '⚠️',
                        'cancelado': '❌'
                    }.get(cuota.estado, '❓')
                    
                    self.stdout.write(f"""
🔢 Cuota {cuota.numero_cuota}:
   • Monto: ${cuota.monto}
   • Estado: {estado_icono} {cuota.estado.upper()}
   • Vencimiento: {cuota.fecha_vencimiento}
   • Pagado: ${cuota.monto_pagado}
                    """)
            
            # Mostrar recomendaciones
            self.stdout.write('\n💡 RECOMENDACIONES:')
            self.stdout.write('=' * 25)
            
            if resumen['colegiatura']['cuotas']['atrasadas'] > 0:
                self.stdout.write('⚠️  El estudiante tiene cuotas atrasadas. Considerar contacto urgente.')
            
            if resumen['colegiatura']['progreso_porcentaje'] < 50:
                self.stdout.write('📉 El estudiante está en las primeras cuotas. Monitorear próximos pagos.')
            
            if resumen['colegiatura']['progreso_porcentaje'] > 80:
                self.stdout.write('📈 El estudiante está cerca de completar el pago. Considerar incentivos.')
            
        except Estudiante.DoesNotExist:
            raise CommandError(f'No existe un estudiante con ID {options["estudiante_id"]}')
        except Evento.DoesNotExist:
            raise CommandError(f'No existe un evento con ID {options["evento_id"]}')
        except Exception as e:
            raise CommandError(f'Error al generar resumen: {str(e)}')
