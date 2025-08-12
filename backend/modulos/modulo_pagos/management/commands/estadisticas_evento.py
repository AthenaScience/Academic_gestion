from django.core.management.base import BaseCommand, CommandError
from modulos.modulo_certificados.models import Evento
from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService


class Command(BaseCommand):
    help = 'Muestra estadísticas completas de pagos para un evento específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--evento_id',
            type=int,
            help='ID del evento',
            required=True
        )
        parser.add_argument(
            '--mostrar_estudiantes_atrasados',
            action='store_true',
            help='Mostrar lista detallada de estudiantes atrasados',
        )

    def handle(self, *args, **options):
        try:
            # Obtener el evento
            evento = Evento.objects.get(id=options['evento_id'])
            
            self.stdout.write(
                self.style.SUCCESS(f'📊 Generando estadísticas para {evento}')
            )
            
            # Obtener las estadísticas usando el servicio
            estadisticas = SistemaPagosService.obtener_estadisticas_evento(evento)
            
            if not estadisticas:
                self.stdout.write(
                    self.style.WARNING('⚠️  No se encontraron planes de pago para este evento')
                )
                return
            
            # Mostrar estadísticas generales
            self.stdout.write(f"""
📈 ESTADÍSTICAS COMPLETAS DEL EVENTO
====================================
📚 EVENTO: {estadisticas['evento']}
📅 FECHA: {evento.fecha_inicio} - {evento.fecha_fin}
💰 COSTOS CONFIGURADOS:
   • Matrícula: ${evento.costo_matricula}
   • Colegiatura: ${evento.costo_colegiatura}
   • Certificado: ${evento.costo_certificado}
   • TOTAL: ${evento.costo_total}

👥 ESTUDIANTES:
   • Total Matriculados: {estadisticas['estudiantes']['total']}
   • Con Plan de Pago: {estadisticas['estudiantes']['matriculados']}

📊 CUOTAS:
   • Total Generadas: {estadisticas['cuotas']['total']}
   • Pagadas: {estadisticas['cuotas']['pagadas']} ✅
   • Pendientes: {estadisticas['cuotas']['pendientes']} ⏳
   • Atrasadas: {estadisticas['cuotas']['atrasadas']} ⚠️

💰 MONTOS:
   • Total Colegiatura: ${estadisticas['montos']['total_colegiatura']}
   • Total Pagado: ${estadisticas['montos']['total_pagado']}
   • Total Pendiente: ${estadisticas['montos']['total_pendiente']}
   • Progreso General: {estadisticas['montos']['progreso_porcentaje']}%
            """)
            
            # Mostrar estudiantes atrasados
            if estadisticas['estudiantes_atrasados']:
                self.stdout.write(f"""
⚠️  ESTUDIANTES ATRASADOS ({len(estadisticas['estudiantes_atrasados'])}):
{'=' * 60}
                """)
                
                for estudiante in estadisticas['estudiantes_atrasados']:
                    self.stdout.write(f"""
👤 {estudiante['estudiante_nombre']}
📚 {estudiante['evento_nombre']}
⚠️  Cuotas Atrasadas: {estudiante['cuotas_atrasadas']}
⏰ Días de Atraso: {estudiante['dias_atraso']}
                    """)
                
                if options.get('mostrar_estudiantes_atrasados'):
                    self.stdout.write('\n📋 DETALLE COMPLETO DE ESTUDIANTES ATRASADOS:')
                    self.stdout.write('=' * 60)
                    
                    for estudiante in estadisticas['estudiantes_atrasados']:
                        self.stdout.write(f"""
🔍 DETALLE DE {estudiante['estudiante_nombre']}:
   • ID Estudiante: {estudiante['estudiante_id']}
   • ID Evento: {estudiante['evento_id']}
   • Cuotas Atrasadas: {estudiante['cuotas_atrasadas']}
   • Días de Atraso: {estudiante['dias_atraso']}
   • Estado: ⚠️  ATRASADO
                        """)
            else:
                self.stdout.write('✅ No hay estudiantes atrasados en este evento')
            
            # Mostrar análisis y recomendaciones
            self.stdout.write('\n💡 ANÁLISIS Y RECOMENDACIONES:')
            self.stdout.write('=' * 40)
            
            progreso = estadisticas['montos']['progreso_porcentaje']
            cuotas_atrasadas = estadisticas['cuotas']['atrasadas']
            total_estudiantes = estadisticas['estudiantes']['total']
            
            if progreso < 30:
                self.stdout.write('📉 El evento está en etapas tempranas. Enfocarse en matrículas y primeras cuotas.')
            
            elif progreso < 70:
                self.stdout.write('📊 El evento está en desarrollo. Monitorear pagos regulares y contactar estudiantes pendientes.')
            
            else:
                self.stdout.write('📈 El evento está avanzado. Enfocarse en cuotas finales y certificados.')
            
            if cuotas_atrasadas > 0:
                porcentaje_atrasados = (cuotas_atrasadas / estadisticas['cuotas']['total']) * 100
                self.stdout.write(f'⚠️  {porcentaje_atrasados:.1f}% de las cuotas están atrasadas. Considerar estrategias de cobranza.')
            
            if total_estudiantes > 0:
                self.stdout.write(f'👥 Promedio de cuotas por estudiante: {estadisticas["cuotas"]["total"] / total_estudiantes:.1f}')
            
            # Mostrar resumen final
            self.stdout.write(f"""
📊 RESUMEN FINAL:
=================
🎯 Estado General: {'✅ EXCELENTE' if progreso > 80 else '📊 BUENO' if progreso > 60 else '⚠️  REQUIERE ATENCIÓN'}
📈 Progreso: {progreso}%
⚠️  Cuotas Atrasadas: {cuotas_atrasadas}
👥 Estudiantes Atrasados: {len(estadisticas['estudiantes_atrasados'])}
            """)
            
        except Evento.DoesNotExist:
            raise CommandError(f'No existe un evento con ID {options["evento_id"]}')
        except Exception as e:
            raise CommandError(f'Error al generar estadísticas: {str(e)}')
