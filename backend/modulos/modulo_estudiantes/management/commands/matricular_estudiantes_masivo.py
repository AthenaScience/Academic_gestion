from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento
from modulos.modulo_pagos.models import EstadoPagosEvento
import csv
import os


class Command(BaseCommand):
    help = 'Matricula masivamente estudiantes desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_file',
            type=str,
            help='Ruta al archivo CSV',
            required=True
        )
        parser.add_argument(
            '--dry_run',
            action='store_true',
            help='Ejecutar en modo simulación (no crear nada)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        if not os.path.exists(csv_file):
            raise CommandError(f'El archivo {csv_file} no existe')
        
        if not csv_file.endswith('.csv'):
            raise CommandError('El archivo debe tener extensión .csv')
        
        self.stdout.write(
            self.style.SUCCESS(f'📚 Iniciando matriculación masiva desde: {csv_file}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODO SIMULACIÓN - No se crearán registros')
            )
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                resultados = []
                errores = []
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Validar campos requeridos
                        if 'nombres' not in row:
                            errores.append({
                                'fila': row_num,
                                'error': 'Falta campo requerido: nombres'
                            })
                            continue
                        
                        # Extraer datos
                        nombre_completo = row['nombres'].strip()
                        if not nombre_completo:
                            errores.append({
                                'fila': row_num,
                                'error': 'El campo nombres no puede estar vacío'
                            })
                            continue
                        
                        nombres, *apellidos_restantes = nombre_completo.split()
                        apellidos = ' '.join(apellidos_restantes) if apellidos_restantes else '---'
                        
                        cedula = row.get('cedula', '').strip()
                        if not cedula:
                            cedula = f"IMP-{row_num:04d}"
                        
                        # Verificar si se proporcionó código de evento
                        codigo_evento = row.get('codigo_evento', '').strip()
                        
                        if codigo_evento:
                            # Buscar evento
                            try:
                                evento = Evento.objects.get(codigo_evento=codigo_evento)
                            except Evento.DoesNotExist:
                                errores.append({
                                    'fila': row_num,
                                    'codigo_evento': codigo_evento,
                                    'error': f'No se encontró un evento con el código: {codigo_evento}'
                                })
                                continue
                            
                            if not dry_run:
                                with transaction.atomic():
                                    # Crear o obtener estudiante
                                    estudiante, creado = Estudiante.objects.get_or_create(
                                        cedula=cedula,
                                        defaults={
                                            'nombres': nombres,
                                            'apellidos': apellidos,
                                            'correo': row.get('correo', f"{cedula}@noemail.com"),
                                            'ciudad': row.get('ciudad', 'Importada'),
                                            'telefono': row.get('telefono', ''),
                                            'codigo_estudiante': f"EST-{cedula[-8:].upper()}"
                                        }
                                    )
                                    
                                    # Verificar si ya está matriculado
                                    if evento in estudiante.eventos_matriculados.all():
                                        errores.append({
                                            'fila': row_num,
                                            'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                                            'cedula': cedula,
                                            'error': f'Ya está matriculado en {evento.nombre}'
                                        })
                                        continue
                                    
                                    # Matricular y crear estado de pagos (sin plan de pago automático)
                                    estudiante.eventos_matriculados.add(evento)
                                    EstadoPagosEvento.objects.get_or_create(
                                        estudiante=estudiante,
                                        evento=evento
                                    )
                                    
                                    resultados.append({
                                        'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                                        'cedula': cedula,
                                        'evento': evento.nombre,
                                        'codigo_evento': evento.codigo_evento,
                                        'matricula_creada': True,
                                        'plan_pago': 'Estándar del evento (ya existe)',
                                        'estudiante_existente': not creado
                                    })
                            
                            else:
                                # Modo simulación
                                resultados.append({
                                    'estudiante': f"{nombres} {apellidos}",
                                    'cedula': cedula,
                                    'evento': evento.nombre,
                                    'codigo_evento': evento.codigo_evento,
                                    'matricula_creada': 'SIMULACIÓN',
                                    'plan_pago': 'Estándar del evento (ya existe)',
                                    'estudiante_existente': 'SIMULACIÓN'
                                })
                        
                        else:
                            # No se proporcionó código de evento - solo crear estudiante
                            if not dry_run:
                                with transaction.atomic():
                                    estudiante, creado = Estudiante.objects.get_or_create(
                                        cedula=cedula,
                                        defaults={
                                            'nombres': nombres,
                                            'apellidos': apellidos,
                                            'correo': row.get('correo', f"{cedula}@noemail.com"),
                                            'ciudad': row.get('ciudad', 'Importada'),
                                            'telefono': row.get('telefono', ''),
                                            'codigo_estudiante': f"EST-{cedula[-8:].upper()}"
                                        }
                                    )
                                    
                                    resultados.append({
                                        'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                                        'cedula': cedula,
                                        'evento': 'Ninguno (sin matricular)',
                                        'codigo_evento': 'No proporcionado',
                                        'matricula_creada': False,
                                        'plan_pago': 'No aplica',
                                        'estudiante_existente': not creado,
                                        'nota': 'Estudiante creado sin matricular a ningún evento'
                                    })
                            
                            else:
                                # Modo simulación
                                resultados.append({
                                    'estudiante': f"{nombres} {apellidos}",
                                    'cedula': cedula,
                                    'evento': 'Ninguno (sin matricular)',
                                    'codigo_evento': 'No proporcionado',
                                    'matricula_creada': 'SIMULACIÓN',
                                    'plan_pago': 'No aplica',
                                    'estudiante_existente': 'SIMULACIÓN',
                                    'nota': 'Estudiante se crearía sin matricular'
                                })
                        
                    except Exception as e:
                        errores.append({
                            'fila': row_num,
                            'error': f'Error inesperado: {str(e)}'
                        })
                
                # Mostrar resultados
                self.stdout.write(
                    self.style.SUCCESS(f'\n📊 RESUMEN DE MATRICULACIÓN MASIVA')
                )
                self.stdout.write('=' * 50)
                self.stdout.write(f'✅ Exitosos: {len(resultados)}')
                self.stdout.write(f'❌ Errores: {len(errores)}')
                self.stdout.write(f'📋 Total procesados: {len(resultados) + len(errores)}')
                
                if resultados:
                    self.stdout.write('\n🎓 ESTUDIANTES PROCESADOS:')
                    self.stdout.write('-' * 30)
                    for resultado in resultados:
                        self.stdout.write(
                            f"• {resultado['estudiante']} ({resultado['cedula']})"
                        )
                        if resultado['evento'] != 'Ninguno (sin matricular)':
                            self.stdout.write(
                                f"  📚 Matriculado en: {resultado['evento']}"
                            )
                            self.stdout.write(
                                f"  💰 Plan de pago: {resultado['plan_pago']}"
                            )
                        else:
                            self.stdout.write(
                                f"  ⚠️  Sin matricular a ningún evento"
                            )
                            if 'nota' in resultado:
                                self.stdout.write(f"  📝 {resultado['nota']}")
                
                if errores:
                    self.stdout.write('\n⚠️  ERRORES ENCONTRADOS:')
                    self.stdout.write('-' * 25)
                    for error in errores:
                        self.stdout.write(
                            f"• Fila {error['fila']}: {error['error']}"
                        )
                
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING('\n🔍 SIMULACIÓN COMPLETADA - No se crearon registros')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('\n🎉 MATRICULACIÓN MASIVA COMPLETADA')
                    )
                
        except Exception as e:
            raise CommandError(f'Error al procesar el archivo CSV: {str(e)}')
