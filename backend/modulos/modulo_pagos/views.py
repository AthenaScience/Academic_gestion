from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    PlanPago,
    Cuota, 
    Pago, 
    EstadoPagosEvento, 
    Matricula,
    Beca,
    Descuento
)
from .serializers import (
    PlanPagoSerializer,
    CuotaSerializer, 
    PagoSerializer, 
    EstadoPagosEventoSerializer, 
    MatriculaSerializer,
    BecaSerializer,
    DescuentoSerializer
)
# Alias temporal para referencias deprecadas en swagger
PlanPagoPersonalizadoSerializer = CuotaSerializer
from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento

# Create your views here.

@swagger_auto_schema(tags=['Planes de Pago'])
class PlanPagoViewSet(viewsets.ModelViewSet):
    queryset = PlanPago.objects.all()
    serializer_class = PlanPagoSerializer
    
    @swagger_auto_schema(
        method='patch',
        operation_description="Reestructura un plan de pago existente cambiando número de cuotas y/o monto",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[],
            properties={
                'nuevo_numero_cuotas': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Nuevo número de cuotas (1-60)',
                    minimum=1,
                    maximum=60
                ),
                'nuevo_monto_colegiatura': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description='Nuevo monto total de colegiatura'
                ),
                'motivo_reestructuracion': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Motivo de la reestructuración del plan'
                ),
                'constancia_reestructuracion': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_BINARY,
                    description='Archivo de constancia de reestructuración'
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Plan reestructurado exitosamente",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'cambios_realizados': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING)
                        ),
                        'plan': PlanPagoSerializer()
                    }
                )
            ),
            400: "Error en los parámetros de reestructuración",
            404: "Plan de pago no encontrado"
        }
    )
    @action(detail=True, methods=['patch'])
    def reestructurar(self, request, pk=None):
        """
        Reestructura un plan de pago existente.
        
        Permite cambiar el número de cuotas y/o monto de colegiatura,
        manteniendo las cuotas ya pagadas y regenerando las pendientes.
        """
        plan = self.get_object()
        
        nuevo_numero_cuotas = request.data.get('nuevo_numero_cuotas')
        nuevo_monto_colegiatura = request.data.get('nuevo_monto_colegiatura')
        motivo_reestructuracion = request.data.get('motivo_reestructuracion')
        constancia_reestructuracion = request.FILES.get('constancia_reestructuracion')
        
        # Validar que al menos un campo de reestructuración esté presente
        if not any([nuevo_numero_cuotas, nuevo_monto_colegiatura, motivo_reestructuracion]):
            return Response(
                {'error': 'Debe especificar al menos un campo para reestructurar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar rangos
        if nuevo_numero_cuotas and not (1 <= nuevo_numero_cuotas <= 60):
            return Response(
                {'error': 'El número de cuotas debe estar entre 1 y 60'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if nuevo_monto_colegiatura and nuevo_monto_colegiatura <= 0:
            return Response(
                {'error': 'El monto de colegiatura debe ser mayor a 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Convertir a Decimal si es necesario
            if nuevo_monto_colegiatura:
                nuevo_monto_colegiatura = Decimal(str(nuevo_monto_colegiatura))
            
            cambios_realizados = plan.reestructurar_plan(
                nuevo_numero_cuotas=nuevo_numero_cuotas,
                nuevo_monto_colegiatura=nuevo_monto_colegiatura,
                motivo_reestructuracion=motivo_reestructuracion,
                constancia_reestructuracion=constancia_reestructuracion
            )
            
            # Refresh del objeto para obtener los datos actualizados
            plan.refresh_from_db()
            
            return Response({
                'message': 'Plan reestructurado exitosamente',
                'cambios_realizados': cambios_realizados,
                'plan': PlanPagoSerializer(plan).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error al reestructurar el plan: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

@swagger_auto_schema(tags=['Cuotas'])
class CuotaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cuotas.
    
    list:
        Obtiene la lista de todas las cuotas.
    
    create:
        Crea una nueva cuota.
    
    retrieve:
        Obtiene los detalles de una cuota específica.
    """
    queryset = Cuota.objects.all()
    serializer_class = CuotaSerializer

    def get_queryset(self):
        queryset = Cuota.objects.all()
        plan_pago_id = self.request.query_params.get('plan_pago', None)
        estado = self.request.query_params.get('estado', None)
        evento_id = self.request.query_params.get('evento', None)
        estudiante_id = self.request.query_params.get('estudiante', None)

        if plan_pago_id:
            queryset = queryset.filter(plan_pago_id=plan_pago_id)
        if evento_id:
            queryset = queryset.filter(plan_pago__evento_id=evento_id)
        if estudiante_id:
            queryset = queryset.filter(plan_pago__estudiante_id=estudiante_id)
        if estado:
            queryset = queryset.filter(estado=estado)

        return queryset

    @swagger_auto_schema(
        operation_description="Obtiene las cuotas pendientes de pago",
        responses={200: CuotaSerializer(many=True)},
        tags=['Cuotas']
    )
    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        """Obtiene la lista de cuotas pendientes de pago."""
        queryset = self.queryset.filter(estado='pendiente')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Obtiene las cuotas atrasadas",
        responses={200: CuotaSerializer(many=True)},
        tags=['Cuotas']
    )
    @action(detail=False, methods=['get'])
    def atrasadas(self, request):
        """Obtiene la lista de cuotas atrasadas."""
        queryset = self.queryset.filter(
            estado='pendiente',
            fecha_vencimiento__lt=timezone.now().date()
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@swagger_auto_schema(tags=['Pagos'])
class PagoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar pagos.
    
    list:
        Obtiene la lista de todos los pagos.
    
    create:
        Registra un nuevo pago.
        
        Parámetros:
        - estudiante: ID del estudiante
        - tipo_pago: Tipo de pago (matricula, cuota, certificado, otro)
        - cuota: ID de la cuota (opcional, requerido solo para pagos de tipo 'cuota')
        - monto: Monto del pago
        - metodo_pago: Método de pago
        - comprobante: Archivo de imagen del comprobante
        - observaciones: Observaciones adicionales
        - numero_transaccion: Número de transacción
    """
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer

    def get_queryset(self):
        queryset = Pago.objects.all()
        estudiante_id = self.request.query_params.get('estudiante', None)
        evento_id = self.request.query_params.get('evento', None)
        tipo_pago = self.request.query_params.get('tipo_pago', None)

        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        if evento_id:
            queryset = queryset.filter(evento_id=evento_id)
        if tipo_pago:
            queryset = queryset.filter(tipo_pago=tipo_pago)

        return queryset

    @swagger_auto_schema(
        request_body=PagoSerializer,
        responses={
            201: PagoSerializer,
            400: "Error en los datos proporcionados"
        },
        tags=['Pagos']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tipo_pago = serializer.validated_data['tipo_pago']
        
        if tipo_pago == 'cuota':
            cuota = serializer.validated_data['cuota']
            monto_pagado = serializer.validated_data['monto']
            
            cuota.monto_pagado += monto_pagado
            if cuota.monto_pagado >= cuota.monto:
                cuota.estado = 'pagado'
                cuota.fecha_pago = timezone.now().date()
            cuota.save()
        elif tipo_pago == 'matricula':
            matricula = Matricula.objects.get(estudiante=serializer.validated_data['estudiante'])
            matricula.matricula_pagada = True
            matricula.save()
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'estudiante_id',
                openapi.IN_QUERY,
                description="ID del estudiante",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: PagoSerializer(many=True),
            400: "ID de estudiante no proporcionado"
        },
        tags=['Pagos']
    )
    @action(detail=False, methods=['get'])
    def por_estudiante(self, request):
        """Obtiene todos los pagos realizados por un estudiante específico."""
        estudiante_id = request.query_params.get('estudiante_id')
        if not estudiante_id:
            return Response({"error": "Se requiere el ID del estudiante"}, status=400)
        
        queryset = self.queryset.filter(estudiante_id=estudiante_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'tipo',
                openapi.IN_QUERY,
                description="Tipo de pago (matricula, cuota, certificado, otro)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: PagoSerializer(many=True),
            400: "Tipo de pago no proporcionado"
        },
        tags=['Pagos']
    )
    @action(detail=False, methods=['get'])
    def por_tipo(self, request):
        """Obtiene todos los pagos de un tipo específico."""
        tipo_pago = request.query_params.get('tipo')
        if not tipo_pago:
            return Response({"error": "Se requiere el tipo de pago"}, status=400)
        
        queryset = self.queryset.filter(tipo_pago=tipo_pago)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@swagger_auto_schema(tags=['Matrículas'])
class MatriculaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar matrículas.
    
    list:
        Obtiene la lista de todas las matrículas.
    
    create:
        Registra una nueva matrícula.
        
        Parámetros:
        - estudiante: ID del estudiante
        - plan_pago: ID del plan de pago
        - fecha_inicio: Fecha de inicio
        - fecha_fin: Fecha de fin
        - observaciones: Observaciones adicionales
    """
    queryset = Matricula.objects.all()
    serializer_class = MatriculaSerializer

    @swagger_auto_schema(
        operation_description="Obtiene las matrículas activas",
        responses={200: MatriculaSerializer(many=True)},
        tags=['Matrículas']
    )
    @action(detail=False, methods=['get'])
    def activas(self, request):
        """Obtiene la lista de matrículas activas."""
        queryset = self.queryset.filter(estado='activa')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Genera las cuotas para una matrícula",
        responses={
            200: openapi.Response(
                description="Cuotas generadas exitosamente",
                examples={
                    "application/json": {
                        "message": "Cuotas generadas exitosamente"
                    }
                }
            )
        },
        tags=['Matrículas']
    )
    @action(detail=True, methods=['post'])
    def generar_cuotas(self, request, pk=None):
        """Genera las cuotas para una matrícula específica."""
        matricula = self.get_object()
        
        if not matricula.plan_pago:
            return Response({"error": "La matrícula no tiene un plan de pago asociado"}, status=400)
        
        plan_pago = matricula.plan_pago
        
        # Verificar si ya existen cuotas para este plan
        if Cuota.objects.filter(plan_pago=plan_pago).exists():
            return Response({"error": "Ya existen cuotas para este plan de pago"}, status=400)
        
        monto_cuota = plan_pago.monto_total / plan_pago.numero_cuotas
        fecha_actual = timezone.now().date()
        
        cuotas_creadas = []
        for i in range(1, plan_pago.numero_cuotas + 1):
            fecha_vencimiento = fecha_actual.replace(day=1)
            fecha_vencimiento = fecha_vencimiento.replace(month=fecha_vencimiento.month + i)
            
            cuota = Cuota.objects.create(
                plan_pago=plan_pago,
                numero_cuota=i,
                monto=monto_cuota,
                fecha_vencimiento=fecha_vencimiento
            )
            cuotas_creadas.append({
                'numero_cuota': cuota.numero_cuota,
                'monto': float(cuota.monto),
                'fecha_vencimiento': cuota.fecha_vencimiento
            })
        
        return Response({
            "message": f"Cuotas generadas exitosamente ({len(cuotas_creadas)} cuotas)",
            "cuotas_creadas": cuotas_creadas
        })

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['metodo_pago'],
            properties={
                'metodo_pago': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Método de pago (efectivo, transferencia, tarjeta, cheque)"
                ),
                'comprobante': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Imagen del comprobante de pago"
                ),
                'observaciones': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Observaciones adicionales"
                ),
                'numero_transaccion': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Número de transacción"
                )
            }
        ),
        responses={
            201: PagoSerializer,
            400: "Error en los datos proporcionados o matrícula ya pagada"
        },
        tags=['Matrículas']
    )
    @action(detail=True, methods=['post'])
    def registrar_pago_matricula(self, request, pk=None):
        """Registra el pago de una matrícula específica."""
        matricula = self.get_object()
        # Usar EstadoPagosEvento como fuente de verdad
        estado_pagos, _ = EstadoPagosEvento.objects.get_or_create(
            estudiante=matricula.estudiante,
            evento=matricula.evento,
        )
        if estado_pagos.matricula_pagada:
            return Response({"error": "La matrícula ya está pagada"}, status=400)
        
        serializer = PagoSerializer(data={
            'estudiante': matricula.estudiante.id,
            'evento': matricula.evento.id,
            'tipo_pago': 'matricula',
            'monto': matricula.evento.costo_matricula,
            'metodo_pago': request.data.get('metodo_pago'),
            'comprobante': request.data.get('comprobante'),
            'observaciones': request.data.get('observaciones', ''),
            'numero_transaccion': request.data.get('numero_transaccion', '')
        })
        
        if serializer.is_valid():
            serializer.save()
            # Marcar en EstadoPagosEvento
            estado_pagos.matricula_pagada = True
            estado_pagos.save()
            # Guardar comprobante si el modelo lo posee
            if hasattr(matricula, 'comprobante_matricula'):
                matricula.comprobante_matricula = request.data.get('comprobante')
                matricula.save(update_fields=['comprobante_matricula'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PlanPagoColegiaturaViewSet(viewsets.ModelViewSet):
    queryset = PlanPago.objects.all()
    serializer_class = PlanPagoSerializer

    def get_queryset(self):
        queryset = PlanPago.objects.all()
        estudiante_id = self.request.query_params.get('estudiante', None)
        evento_id = self.request.query_params.get('evento', None)

        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        if evento_id:
            queryset = queryset.filter(evento_id=evento_id)

        return queryset

    @action(detail=True, methods=['get'])
    def cuotas(self, request, pk=None):
        plan_pago = self.get_object()
        cuotas = Cuota.objects.filter(plan_pago=plan_pago)
        serializer = CuotaSerializer(cuotas, many=True)
        return Response(serializer.data)

class EstadoPagosEventoViewSet(viewsets.ModelViewSet):
    queryset = EstadoPagosEvento.objects.all()
    serializer_class = EstadoPagosEventoSerializer

    def get_queryset(self):
        queryset = EstadoPagosEvento.objects.all()
        estudiante_id = self.request.query_params.get('estudiante', None)
        evento_id = self.request.query_params.get('evento', None)

        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        if evento_id:
            queryset = queryset.filter(evento_id=evento_id)

        return queryset

@swagger_auto_schema(tags=['Becas'])
class BecaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar becas de estudiantes.
    
    list:
        Obtiene la lista de todas las becas.
    
    create:
        Crea una nueva beca para un estudiante en un evento específico.
        
        Parámetros:
        - estudiante: ID del estudiante
        - evento: ID del evento
        - nombre_beca: Nombre de la beca
        - tipo_beca: Tipo de beca (porcentual, monto_fijo, combinada)
        - porcentaje_descuento: Porcentaje de descuento (0-100)
        - monto_descuento: Monto fijo de descuento
        - aplica_matricula: ¿Aplica a matrícula?
        - aplica_colegiatura: ¿Aplica a colegiatura?
        - aplica_certificado: ¿Aplica a certificado?
        - fecha_inicio: Fecha de inicio de la beca
        - fecha_fin: Fecha de fin de la beca
        - motivo: Motivo de la beca
        - aprobado_por: Quien aprobó la beca
    """
    queryset = Beca.objects.all()
    serializer_class = BecaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estudiante', 'evento', 'tipo_beca', 'estado']
    search_fields = ['nombre_beca', 'motivo', 'aprobado_por']
    ordering_fields = ['fecha_creacion', 'fecha_inicio', 'fecha_fin']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por estudiante si se especifica
        estudiante_id = self.request.query_params.get('estudiante_id')
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        
        # Filtrar por evento si se especifica
        evento_id = self.request.query_params.get('evento_id')
        if evento_id:
            queryset = queryset.filter(evento_id=evento_id)
        
        # Filtrar solo becas activas si se especifica
        solo_activas = self.request.query_params.get('solo_activas', 'false').lower() == 'true'
        if solo_activas:
            queryset = queryset.filter(estado='activa')
        
        return queryset

    @swagger_auto_schema(
        operation_description="Obtiene las becas activas y vigentes",
        responses={200: BecaSerializer(many=True)},
        tags=['Becas']
    )
    @action(detail=False, methods=['get'])
    def activas(self, request):
        """Obtiene la lista de becas activas y vigentes."""
        hoy = timezone.now().date()
        queryset = self.queryset.filter(
            estado='activa',
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Obtiene las becas por estudiante y evento",
        manual_parameters=[
            openapi.Parameter(
                'estudiante_id',
                openapi.IN_QUERY,
                description="ID del estudiante",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'evento_id',
                openapi.IN_QUERY,
                description="ID del evento",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={200: BecaSerializer(many=True)},
        tags=['Becas']
    )
    @action(detail=False, methods=['get'])
    def por_estudiante_evento(self, request):
        """Obtiene las becas de un estudiante específico en un evento específico."""
        estudiante_id = request.query_params.get('estudiante_id')
        evento_id = request.query_params.get('evento_id')
        
        if not estudiante_id or not evento_id:
            return Response(
                {"error": "Se requieren estudiante_id y evento_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.queryset.filter(
            estudiante_id=estudiante_id,
            evento_id=evento_id,
            estado='activa'
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Calcula el descuento total aplicable para un tipo de pago",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estudiante_id', 'evento_id', 'tipo_pago', 'monto_original'],
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'evento_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'tipo_pago': openapi.Schema(type=openapi.TYPE_STRING, enum=['matricula', 'colegiatura', 'certificado']),
                'monto_original': openapi.Schema(type=openapi.TYPE_NUMBER)
            }
        ),
        responses={
            200: openapi.Response(
                description="Descuento calculado",
                examples={
                    "application/json": {
                        "descuento_total": "25.00",
                        "monto_final": "75.00",
                        "becas_aplicadas": [
                            {"nombre": "Beca Excelencia", "descuento": "25.00"}
                        ]
                    }
                }
            )
        },
        tags=['Becas']
    )
    @action(detail=False, methods=['post'])
    def calcular_descuento(self, request):
        """Calcula el descuento total aplicable para un tipo de pago específico."""
        estudiante_id = request.data.get('estudiante_id')
        evento_id = request.data.get('evento_id')
        tipo_pago = request.data.get('tipo_pago')
        monto_original = request.data.get('monto_original')
        
        if not all([estudiante_id, evento_id, tipo_pago, monto_original]):
            return Response(
                {"error": "Todos los campos son requeridos"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener becas activas del estudiante en el evento
        becas = self.queryset.filter(
            estudiante_id=estudiante_id,
            evento_id=evento_id,
            estado='activa'
        )
        
        descuento_total = Decimal('0.00')
        becas_aplicadas = []
        
        for beca in becas:
            descuento = beca.calcular_descuento(monto_original, tipo_pago)
            if descuento > 0:
                descuento_total += descuento
                becas_aplicadas.append({
                    'nombre': beca.nombre_beca,
                    'descuento': str(descuento),
                    'tipo': beca.tipo_beca
                })
        
        monto_final = monto_original - descuento_total
        
        return Response({
            'descuento_total': str(descuento_total),
            'monto_final': str(monto_final),
            'becas_aplicadas': becas_aplicadas
        })

@swagger_auto_schema(tags=['Descuentos'])
class DescuentoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar descuentos de estudiantes.
    
    list:
        Obtiene la lista de todos los descuentos.
    
    create:
        Crea un nuevo descuento para un estudiante en un evento específico.
        
        Parámetros:
        - estudiante: ID del estudiante
        - evento: ID del evento
        - nombre_descuento: Nombre del descuento
        - tipo_descuento: Tipo de descuento (porcentual, monto_fijo)
        - porcentaje_descuento: Porcentaje de descuento (0-100)
        - monto_descuento: Monto fijo de descuento
        - aplica_matricula: ¿Aplica a matrícula?
        - aplica_colegiatura: ¿Aplica a colegiatura?
        - aplica_certificado: ¿Aplica a certificado?
        - fecha_inicio: Fecha de inicio del descuento
        - fecha_fin: Fecha de fin del descuento
        - motivo: Motivo del descuento
        - codigo_promocional: Código promocional si aplica
    """
    queryset = Descuento.objects.all()
    serializer_class = DescuentoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estudiante', 'evento', 'tipo_descuento', 'estado']
    search_fields = ['nombre_descuento', 'motivo', 'codigo_promocional']
    ordering_fields = ['fecha_creacion', 'fecha_inicio', 'fecha_fin']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por estudiante si se especifica
        estudiante_id = self.request.query_params.get('estudiante_id')
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        
        # Filtrar por evento si se especifica
        evento_id = self.request.query_params.get('evento_id')
        if evento_id:
            queryset = queryset.filter(evento_id=evento_id)
        
        # Filtrar solo descuentos activos si se especifica
        solo_activos = self.request.query_params.get('solo_activos', 'false').lower() == 'true'
        if solo_activos:
            queryset = queryset.filter(estado='activo')
        
        return queryset

    @swagger_auto_schema(
        operation_description="Obtiene los descuentos activos y vigentes",
        responses={200: DescuentoSerializer(many=True)},
        tags=['Descuentos']
    )
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """Obtiene la lista de descuentos activos y vigentes."""
        hoy = timezone.now().date()
        queryset = self.queryset.filter(
            estado='activo',
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Obtiene descuentos por código promocional",
        manual_parameters=[
            openapi.Parameter(
                'codigo',
                openapi.IN_QUERY,
                description="Código promocional",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={200: DescuentoSerializer(many=True)},
        tags=['Descuentos']
    )
    @action(detail=False, methods=['get'])
    def por_codigo(self, request):
        """Obtiene descuentos por código promocional."""
        codigo = request.query_params.get('codigo')
        if not codigo:
            return Response(
                {"error": "Se requiere el código promocional"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.queryset.filter(
            codigo_promocional=codigo,
            estado='activo'
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@swagger_auto_schema(tags=['Planes de Pago Personalizados'])
class PlanPagoPersonalizadoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar planes de pago personalizados.
    
    list:
        Obtiene la lista de todos los planes de pago personalizados.
    
    create:
        Crea un nuevo plan de pago personalizado para un estudiante.
        
        Parámetros:
        - estudiante: ID del estudiante
        - evento: ID del evento
        - tipo_plan: Tipo de plan (cuotas_especiales, plan_flexible, convenio_institucional, otro)
        - numero_cuotas_personalizado: Número de cuotas personalizado
        - monto_matricula_personalizado: Monto de matrícula personalizado (opcional)
        - monto_colegiatura_personalizado: Monto de colegiatura personalizado (opcional)
        - fecha_inicio: Fecha de inicio del plan
        - fecha_fin: Fecha de fin del plan
        - motivo: Motivo del plan personalizado
        - aprobado_por: Quien aprobó el plan
        - documentos_soporte: Documentos de soporte (opcional)
    
    retrieve:
        Obtiene los detalles de un plan de pago personalizado específico.
    
    update:
        Actualiza un plan de pago personalizado existente.
    
    partial_update:
        Actualiza parcialmente un plan de pago personalizado existente.
    
    destroy:
        Elimina un plan de pago personalizado.
    """
    queryset = []
    serializer_class = CuotaSerializer  # dummy serializer para evitar NameError
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estudiante', 'evento', 'tipo_plan', 'estado']
    search_fields = ['motivo', 'aprobado_por']
    ordering_fields = ['fecha_creacion', 'fecha_inicio', 'fecha_fin']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por estudiante si se especifica
        estudiante_id = self.request.query_params.get('estudiante_id')
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        
        # Filtrar por evento si se especifica
        evento_id = self.request.query_params.get('evento_id')
        if evento_id:
            queryset = queryset.filter(evento_id=evento_id)
        
        # Filtrar solo planes activos si se especifica
        solo_activos = self.request.query_params.get('solo_activos', 'false').lower() == 'true'
        if solo_activos:
            queryset = queryset.filter(estado='activo')
        
        return queryset

    @swagger_auto_schema(
        operation_description="Obtiene los planes de pago personalizados activos y vigentes",
        responses={200: PlanPagoPersonalizadoSerializer(many=True)},
        tags=['Planes de Pago Personalizados']
    )
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """Obtiene la lista de planes de pago personalizados activos y vigentes."""
        hoy = timezone.now().date()
        return Response([])

    @swagger_auto_schema(
        operation_description="Obtiene el plan personalizado de un estudiante en un evento específico",
        manual_parameters=[
            openapi.Parameter(
                'estudiante_id',
                openapi.IN_QUERY,
                description="ID del estudiante",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'evento_id',
                openapi.IN_QUERY,
                description="ID del evento",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={200: PlanPagoPersonalizadoSerializer},
        tags=['Planes de Pago Personalizados']
    )
    @action(detail=False, methods=['get'])
    def por_estudiante_evento(self, request):
        """Obtiene el plan de pago personalizado de un estudiante específico en un evento específico."""
        estudiante_id = request.query_params.get('estudiante_id')
        evento_id = request.query_params.get('evento_id')
        
        if not estudiante_id or not evento_id:
            return Response(
                {"error": "Se requieren estudiante_id y evento_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({"error": "Planes personalizados deprecados"}, status=status.HTTP_410_GONE)

    @swagger_auto_schema(
        operation_description="Calcula el número de cuotas y montos a aplicar para un estudiante",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estudiante_id', 'evento_id'],
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'evento_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={
            200: openapi.Response(
                description="Configuración de pagos calculada",
                examples={
                    "application/json": {
                        "numero_cuotas": 6,
                        "monto_matricula": "50.00",
                        "monto_colegiatura": "100.00",
                        "tiene_plan_personalizado": True,
                        "plan_aplicado": "Plan Flexible"
                    }
                }
            )
        },
        tags=['Planes de Pago Personalizados']
    )
    @action(detail=False, methods=['post'])
    def calcular_configuracion_pagos(self, request):
        """Calcula la configuración de pagos (cuotas y montos) para un estudiante en un evento."""
        estudiante_id = request.data.get('estudiante_id')
        evento_id = request.data.get('evento_id')
        
        if not estudiante_id or not evento_id:
            return Response(
                {"error": "Se requieren estudiante_id y evento_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({"error": "Planes personalizados deprecados"}, status=status.HTTP_410_GONE)

    @swagger_auto_schema(
        operation_description="Obtiene el resumen detallado del plan de pagos de un estudiante",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estudiante_id', 'evento_id'],
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'evento_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={
            200: openapi.Response(
                description="Resumen del plan de pagos",
                examples={
                    "application/json": {
                        "tipo": "personalizado",
                        "numero_cuotas": 20,
                        "monto_matricula": "50.00",
                        "monto_colegiatura": "100.00",
                        "monto_cuota_matricula": "2.50",
                        "monto_cuota_colegiatura": "5.00",
                        "tipo_plan": "Plan Flexible",
                        "motivo": "Dificultades económicas"
                    }
                }
            )
        },
        tags=['Planes de Pago Personalizados']
    )
    @action(detail=False, methods=['post'])
    def resumen_plan_pagos(self, request):
        """Obtiene el resumen detallado del plan de pagos de un estudiante en un evento."""
        estudiante_id = request.data.get('estudiante_id')
        evento_id = request.data.get('evento_id')
        
        if not estudiante_id or not evento_id:
            return Response(
                {"error": "Se requieren estudiante_id y evento_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({"error": "Planes personalizados deprecados"}, status=status.HTTP_410_GONE)
