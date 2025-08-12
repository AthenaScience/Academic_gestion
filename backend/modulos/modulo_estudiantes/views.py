from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Estudiante
#importando el modelo Evento
from modulos.modulo_certificados.models import Evento
#from .models import Evento

from .serializers import EstudianteSerializer
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import JsonResponse
import csv
import os
import uuid as uuid_lib
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from modulos.modulo_pagos.models import EstadoPagosEvento, Pago, Cuota, PlanPago, Matricula
from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService
from modulos.modulo_pagos.serializers import MatriculaSerializer, PagoSerializer, CuotaSerializer
from django.db.models import Sum, Q

@swagger_auto_schema(tags=['Estudiantes'])
class EstudianteViewSet(viewsets.ModelViewSet):
    queryset = Estudiante.objects.all()
    serializer_class = EstudianteSerializer

    @swagger_auto_schema(
        operation_description="Obtiene la información de pagos de un estudiante",
        responses={200: "Información de pagos del estudiante"},
        tags=['Estudiantes']
    )
    @action(detail=True, methods=['get'])
    def pagos(self, request, pk=None):
        """Obtiene toda la información de pagos de un estudiante."""
        estudiante = self.get_object()
        
        # Obtener estados de pago por evento
        estados_pago = EstadoPagosEvento.objects.filter(estudiante=estudiante)
        
        # Obtener pagos
        pagos = Pago.objects.filter(estudiante=estudiante)
        pagos_serializer = PagoSerializer(pagos, many=True)
        
        # Obtener cuotas pendientes
        cuotas_pendientes = Cuota.objects.filter(plan_pago__estudiante=estudiante, estado='pendiente')
        cuotas_serializer = CuotaSerializer(cuotas_pendientes, many=True)
        
        # Calcular total pagado
        total_pagado = pagos.aggregate(total=Sum('monto'))['total'] or 0
        
        # Calcular total pendiente
        total_pendiente = cuotas_pendientes.aggregate(
            total=Sum('monto')
        )['total'] or 0

        # Preparar resumen por evento
        resumen_eventos = []
        for estado in estados_pago:
            evento = estado.evento
            pagos_evento = pagos.filter(evento=evento)
            cuotas_evento = cuotas_pendientes.filter(plan_pago__evento=evento)
            
            resumen_eventos.append({
                'evento': {
                    'id': evento.id,
                    'nombre': evento.nombre,
                    'tipo': evento.tipo,
                    'costo_matricula': float(evento.costo_matricula),
                    'costo_colegiatura': float(evento.costo_colegiatura),
                    'costo_certificado': float(evento.costo_certificado),
                },
                'estado_pagos': {
                    'matricula_pagada': estado.matricula_pagada,
                    'certificado_pagado': estado.certificado_pagado,
                    'colegiatura_al_dia': estado.colegiatura_al_dia,
                },
                'pagos': pagos_serializer.data,
                'cuotas_pendientes': cuotas_serializer.data,
                'total_pagado': float(pagos_evento.aggregate(total=Sum('monto'))['total'] or 0),
                'total_pendiente': float(cuotas_evento.aggregate(total=Sum('monto'))['total'] or 0)
            })
        
        return Response({
            'resumen_eventos': resumen_eventos,
            'total_pagado': float(total_pagado),
            'total_pendiente': float(total_pendiente)
        })

    @swagger_auto_schema(
        operation_description="Opciones de pago disponibles (matrícula, cuotas pendientes, certificado, misceláneos) para un estudiante en un evento.",
        manual_parameters=[
            openapi.Parameter('evento_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True),
        ],
        responses={200: 'OK'},
        tags=['Estudiantes']
    )
    @action(detail=True, methods=['get'])
    def pagables(self, request, pk=None):
        estudiante = self.get_object()
        evento_id = request.query_params.get('evento_id')
        if not evento_id:
            return Response({'error': 'evento_id es requerido'}, status=400)
        try:
            evento = Evento.objects.get(pk=evento_id)
        except Evento.DoesNotExist:
            return Response({'error': 'Evento no encontrado'}, status=404)

        # Matrícula
        estado = EstadoPagosEvento.objects.filter(estudiante=estudiante, evento=evento).first()
        matricula_pagable = bool(evento.requiere_matricula and not (estado and estado.matricula_pagada))

        # Cuotas pendientes
        cuotas = Cuota.objects.filter(
            plan_pago__estudiante=estudiante,
            plan_pago__evento=evento,
            estado='pendiente',
        ).order_by('numero_cuota')

        # Certificado
        certificado_pagable = True  # la elegibilidad total se valida en endpoints de certificados

        # Misceláneos (por estudiante, fuera del curso)
        miscelaneos = []  # libres; se usarán observaciones/monto

        return Response({
            'evento': {'id': evento.id, 'nombre': evento.nombre, 'tipo': evento.tipo},
            'matricula': {
                'pagable': matricula_pagable,
                'monto': float(evento.costo_matricula),
            },
            'cuotas_pendientes': [
                {
                    'id': c.id,
                    'numero_cuota': c.numero_cuota,
                    'monto': float(c.monto),
                    'fecha_vencimiento': c.fecha_vencimiento,
                }
                for c in cuotas
            ],
            'certificado': {
                'pagable': certificado_pagable,
                'monto': float(evento.costo_certificado),
            },
            'miscelaneos': miscelaneos,
        })

    @swagger_auto_schema(
        operation_description="Registra un nuevo pago para el estudiante",
        request_body=PagoSerializer,
        responses={
            201: PagoSerializer,
            400: "Error en los datos proporcionados"
        },
        tags=['Estudiantes']
    )
    @action(detail=True, methods=['post'])
    def registrar_pago(self, request, pk=None):
        """Registra un nuevo pago para el estudiante."""
        estudiante = self.get_object()
        request.data['estudiante'] = estudiante.id
        
        serializer = PagoSerializer(data=request.data)
        if serializer.is_valid():
            pago = serializer.save()
            
            # Actualizar estado de pagos del evento
            estado_pagos, _ = EstadoPagosEvento.objects.get_or_create(
                estudiante=estudiante,
                evento=pago.evento
            )
            
            if pago.tipo_pago == 'matricula':
                estado_pagos.matricula_pagada = True
            elif pago.tipo_pago == 'certificado':
                estado_pagos.certificado_pagado = True
            elif pago.tipo_pago == 'cuota':
                # Verificar si todas las cuotas están al día
                cuotas_pendientes = Cuota.objects.filter(
                    plan_pago__estudiante=estudiante,
                    plan_pago__evento=pago.evento,
                    estado='pendiente'
                ).exists()
                estado_pagos.colegiatura_al_dia = not cuotas_pendientes
            
            estado_pagos.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Obtiene el historial de pagos del estudiante",
        responses={200: PagoSerializer(many=True)},
        tags=['Estudiantes']
    )
    @action(detail=True, methods=['get'])
    def historial_pagos(self, request, pk=None):
        """Obtiene el historial completo de pagos del estudiante."""
        estudiante = self.get_object()
        pagos = Pago.objects.filter(estudiante=estudiante).order_by('-fecha_pago')
        serializer = PagoSerializer(pagos, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Obtiene las cuotas pendientes del estudiante",
        responses={200: CuotaSerializer(many=True)},
        tags=['Estudiantes']
    )
    @action(detail=True, methods=['get'])
    def cuotas_pendientes(self, request, pk=None):
        """Obtiene las cuotas pendientes del estudiante."""
        estudiante = self.get_object()
        cuotas = Cuota.objects.filter(plan_pago__estudiante=estudiante, estado='pendiente').order_by('fecha_vencimiento')
        serializer = CuotaSerializer(cuotas, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Obtiene las matrículas activas del estudiante",
        responses={200: MatriculaSerializer(many=True)},
        tags=['Estudiantes']
    )
    @action(detail=True, methods=['get'])
    def matriculas_activas(self, request, pk=None):
        """Obtiene las matrículas activas del estudiante."""
        estudiante = self.get_object()
        matriculas = Matricula.objects.filter(
            estudiante=estudiante,
            estado='activa'
        )
        serializer = MatriculaSerializer(matriculas, many=True)
        return Response(serializer.data)

class CargaEstudiantesAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Carga masiva de estudiantes desde un archivo CSV. Si se proporciona código de evento, se matricula automáticamente.",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True, description='Archivo CSV con los datos'),
        ],
        responses={200: 'OK'},
        tags = ['Carga Masiva Estudiantes']
    )
    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'Archivo CSV no encontrado'}, status=400)

        uploaded_file = request.FILES['file']
        if not uploaded_file.name.endswith('.csv'):
            return JsonResponse({'error': 'El archivo debe tener extensión .csv'}, status=400)

        decoded_file = uploaded_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        resultados = []
        errores = []

        for row_num, row in enumerate(reader, start=2):  # start=2 porque row 1 es el header
            try:
                # Validar campos requeridos
                if 'nombres' not in row:
                    errores.append({
                        'fila': row_num,
                        'error': 'Falta campo requerido: nombres'
                    })
                    continue

                # Extraer datos del estudiante
                nombre_completo = row['nombres'].strip()
                if not nombre_completo:
                    errores.append({
                        'fila': row_num,
                        'error': 'El campo nombres no puede estar vacío'
                    })
                    continue

                nombres, *apellidos_restantes = nombre_completo.split()
                apellidos = ' '.join(apellidos_restantes) if apellidos_restantes else '---'
                
                # Generar cédula única si no se proporciona
                cedula = row.get('cedula', '').strip()
                if not cedula:
                    cedula = f"IMP-{uuid_lib.uuid4().hex[:8].upper()}"
                
                # Generar correo si no se proporciona
                correo = row.get('correo', '').strip()
                if not correo:
                    correo = f"{cedula}@noemail.com"
                
                # Generar código de estudiante único
                codigo_unico = f"EST-{uuid_lib.uuid4().hex[:8].upper()}"

                # Crear o obtener estudiante
                estudiante, creado = Estudiante.objects.get_or_create(
                    cedula=cedula,
                    defaults={
                        'nombres': nombres,
                        'apellidos': apellidos,
                        'correo': correo,
                        'ciudad': row.get('ciudad', 'Importada').strip(),
                        'telefono': row.get('telefono', '').strip(),
                        'codigo_estudiante': codigo_unico
                    }
                )

                # Verificar si se proporcionó código de evento
                codigo_evento = row.get('codigo_evento', '').strip()
                
                if codigo_evento:
                    # Buscar evento por código
                    try:
                        evento = Evento.objects.get(codigo_evento=codigo_evento)
                        
                        # Verificar si ya está matriculado en este evento
                        if evento in estudiante.eventos_matriculados.all():
                            errores.append({
                                'fila': row_num,
                                'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                                'cedula': cedula,
                                'error': f'Ya está matriculado en el evento {evento.nombre}'
                            })
                            continue
                        
                        # Matricular al estudiante en el evento (dispara señal que crea plan estándar)
                        estudiante.eventos_matriculados.add(evento)

                        # Asegurar estado de pagos y plan estándar
                        estado_pagos, _ = EstadoPagosEvento.objects.get_or_create(
                            estudiante=estudiante,
                            evento=evento
                        )

                        plan = PlanPago.objects.filter(estudiante=estudiante, evento=evento).first()
                        if not plan:
                            try:
                                SistemaPagosService.crear_plan_pago_estudiante(
                                    estudiante=estudiante,
                                    evento=evento,
                                )
                                plan = PlanPago.objects.filter(estudiante=estudiante, evento=evento).first()
                            except Exception:
                                plan = None

                        resultados.append({
                            'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                            'cedula': estudiante.cedula,
                            'evento': evento.nombre,
                            'codigo_evento': evento.codigo_evento,
                            'matricula_creada': True,
                            'plan_pago_creado': bool(plan),
                            'numero_cuotas': plan.numero_cuotas if plan else None,
                            'estudiante_existente': not creado
                        })
                        
                    except Evento.DoesNotExist:
                        errores.append({
                            'fila': row_num,
                            'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                            'cedula': cedula,
                            'codigo_evento': codigo_evento,
                            'error': f'No se encontró un evento con el código: {codigo_evento}'
                        })
                        continue
                        
                else:
                    # No se proporcionó código de evento - solo crear estudiante
                    if creado:
                        resultados.append({
                            'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                            'cedula': estudiante.cedula,
                            'evento': 'Ninguno (sin matricular)',
                            'codigo_evento': 'No proporcionado',
                            'matricula_creada': False,
                            'plan_pago': 'No aplica',
                            'estudiante_existente': False,
                            'nota': 'Estudiante creado sin matricular a ningún evento'
                        })
                    else:
                        resultados.append({
                            'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                            'cedula': cedula,
                            'evento': 'Ninguno (sin matricular)',
                            'codigo_evento': 'No proporcionado',
                            'matricula_creada': False,
                            'plan_pago': 'No aplica',
                            'estudiante_existente': True,
                            'nota': 'Estudiante existente sin cambios'
                        })

            except Exception as e:
                errores.append({
                    'fila': row_num,
                    'row': row,
                    'error': f'Error inesperado: {str(e)}'
                })

        return JsonResponse({
            'estado': 'completado',
            'creados': resultados,
            'errores': errores,
            'total_procesados': len(resultados) + len(errores),
            'exitosos': len(resultados),
            'fallidos': len(errores)
        })