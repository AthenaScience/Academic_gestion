from django.core.management.base import BaseCommand
from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService


class Command(BaseCommand):
    help = 'Verifica y marca las cuotas que están atrasadas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--evento_id',
            type=int,
            help='ID del evento específico (opcional)',
            required=False
        )
        parser.add_argument(
            '--mostrar_estudiantes',
            action='store_true',
            help='Mostrar lista de estudiantes atrasados',
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write(
                self.style.SUCCESS('🔍 Verificando cuotas atrasadas...')
            )
            
            # Verificar cuotas atrasadas
            cuotas_atrasadas = SistemaPagosService.verificar_cuotas_atrasadas()
            
            if cuotas_atrasadas:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Se encontraron {len(cuotas_atrasadas)} cuotas atrasadas')
                )
                
                # Mostrar detalles de las cuotas atrasadas
                for cuota in cuotas_atrasadas:
                    self.stdout.write(f"""
📅 CUOTA ATRASADA:
==================
👤 Estudiante: {cuota.estudiante}
📚 Evento: {cuota.evento}
🔢 Cuota: {cuota.numero_cuota}
💰 Monto: ${cuota.monto}
📅 Vencimiento: {cuota.fecha_vencimiento}
⏰ Días de Atraso: {(cuota.fecha_vencimiento - cuota.fecha_vencimiento).days}
                    """)
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ No se encontraron cuotas atrasadas')
                )
            
            # Mostrar estudiantes atrasados si se solicita
            if options.get('mostrar_estudiantes'):
                self.stdout.write('\n📊 ESTUDIANTES ATRASADOS:')
                self.stdout.write('=' * 50)
                
                estudiantes_atrasados = SistemaPagosService.obtener_estudiantes_atrasados()
                
                if estudiantes_atrasados:
                    for estudiante in estudiantes_atrasados:
                        self.stdout.write(f"""
👤 {estudiante['estudiante_nombre']}
📚 {estudiante['evento_nombre']}
⚠️  Cuotas Atrasadas: {estudiante['cuotas_atrasadas']}
⏰ Días de Atraso: {estudiante['dias_atraso']}
                        """)
                else:
                    self.stdout.write('✅ No hay estudiantes atrasados')
            
            # Mostrar resumen general
            self.stdout.write('\n📈 RESUMEN GENERAL:')
            self.stdout.write('=' * 30)
            self.stdout.write(f'🔍 Cuotas Verificadas: {len(cuotas_atrasadas)} atrasadas')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al verificar cuotas atrasadas: {str(e)}')
            )
