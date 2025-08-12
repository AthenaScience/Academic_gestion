from django.shortcuts import render
from django.http import HttpResponse
import os
import csv
import uuid as uuid_lib
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import Certificado
from .services.pdf_generator import generar_certificado, generar_certificado_bytes, generar_constancia_bytes
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files import File
from django.core.files.base import ContentFile
from django.views.decorators.http import require_POST
from .models import Evento
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Evento
from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_pagos.models import EstadoPagosEvento, Matricula
from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService
from django.db.models import Q
from .serializers import EventoSerializer, CertificadoSerializer
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from modulos.modulo_estudiantes.models import Estudiante
import zipfile
import tempfile
from io import BytesIO
import qrcode
import json
import datetime as dt


def _ensure_qr_bytes_and_persist(certificado, request) -> bytes:
    """Devuelve los bytes del QR para el certificado.
    Si no existe en BD, lo genera, lo guarda en `certificado.qr` y retorna los bytes.
    """
    # Si ya existe archivo QR, retornarlo
    try:
        if certificado.qr and getattr(certificado.qr, 'path', None) and os.path.exists(certificado.qr.path):
            with open(certificado.qr.path, 'rb') as f:
                return f.read()
    except Exception:
        pass

    # Generar QR determinista
    codigo = certificado.codigo_certificado
    # Enlazar directamente al PDF público del certificado
    # Apuntar a la nueva pagina de constancia (HTML) que embebe un PDF de constancia
    pdf_path = f"/api/v1/certificados/constancia/?codigo={codigo}"
    payload = request.build_absolute_uri(pdf_path)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_bytes = buffer.getvalue()

    # Guardar archivo en el FileField para persistirlo
    try:
        filename = f"{certificado.codigo_certificado}.png"
        certificado.qr.save(filename, ContentFile(qr_bytes), save=True)
    except Exception:
        # Si fallara el guardado, al menos devolver los bytes para el PDF
        pass

    return qr_bytes


# Create your views here.
def inicio(request):
    return HttpResponse("Bienvenido al sistema de gestión académica")


def generar_certificado_view(request, uuid):
    certificado = get_object_or_404(Certificado, uuid=uuid)
    if not certificado.foto or not certificado.qr:
        return HttpResponse("Falta la foto o el QR en el certificado.", status=400)
    ruta_foto = certificado.foto.path
    ruta_qr = certificado.qr.path

    output_path = generar_certificado(certificado.estudiante, certificado, ruta_foto, ruta_qr)

    with open(output_path, 'rb') as f:
        # certificado.archivo_pdf.save(os.path.basename(output_path), File(f), save=True)
        pass

    return HttpResponse(f"Certificado generado con éxito. PDF: {certificado.archivo_pdf.url}")


class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer

    @swagger_auto_schema(
        operation_description="Lista estudiantes del evento con su estado de pagos y resumen de colegiatura",
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, description='Búsqueda por nombre/apellido/cédula'),
            openapi.Parameter('estado', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, description='Filtro por estado_general: al_dia | atrasado | completado | pendiente')
        ],
        responses={200: 'OK'},
        tags=["Eventos"]
    )
    @action(detail=True, methods=['get'], url_path='estudiantes-pagos')
    def estudiantes_pagos(self, request, pk=None):
        evento = self.get_object()

        # Base: estudiantes asociados al evento por M2M o por matrícula
        estudiantes_qs = Estudiante.objects.filter(
            Q(eventos_matriculados=evento) | Q(matriculas__evento=evento)
        ).distinct()

        # Búsqueda opcional
        query = request.query_params.get('q')
        if query:
            estudiantes_qs = estudiantes_qs.filter(
                Q(nombres__icontains=query) | Q(apellidos__icontains=query) | Q(cedula__icontains=query)
            )

        filtro_estado = (request.query_params.get('estado') or '').strip()

        resultados = []
        for est in estudiantes_qs:
            resumen = SistemaPagosService.obtener_resumen_estudiante(est, evento)
            estado_pagos = EstadoPagosEvento.objects.filter(estudiante=est, evento=evento).first()

            item_estado = {
                'matricula_pagada': bool(estado_pagos.matricula_pagada) if estado_pagos else False,
                'certificado_pagado': bool(estado_pagos.certificado_pagado) if estado_pagos else False,
                'colegiatura_al_dia': bool(estado_pagos.colegiatura_al_dia) if estado_pagos else False,
                'estado_general': resumen['estado_general'] if resumen else 'pendiente'
            }

            if filtro_estado and item_estado['estado_general'] != filtro_estado:
                continue

            if resumen:
                colegiatura = resumen['colegiatura']
                cuotas = colegiatura['cuotas']
                payload_colegiatura = {
                    'monto_total': str(colegiatura['monto_total']),
                    'monto_pagado': str(colegiatura['monto_pagado']),
                    'monto_pendiente': str(colegiatura['monto_pendiente']),
                    'progreso_porcentaje': colegiatura['progreso_porcentaje'],
                    'cuotas': cuotas,
                }
            else:
                payload_colegiatura = {
                    'monto_total': str(evento.costo_colegiatura),
                    'monto_pagado': '0.00',
                    'monto_pendiente': str(evento.costo_colegiatura),
                    'progreso_porcentaje': 0,
                    'cuotas': {'total': 0, 'pagadas': 0, 'pendientes': 0, 'atrasadas': 0}
                }

            resultados.append({
                'estudiante': {
                    'id': est.id,
                    'nombres': est.nombres,
                    'apellidos': est.apellidos,
                    'cedula': est.cedula,
                },
                'estado_pagos': item_estado,
                'colegiatura': payload_colegiatura,
            })

        return Response({'evento': {'id': evento.id, 'nombre': evento.nombre}, 'estudiantes': resultados})

    @swagger_auto_schema(
        operation_description="Estadísticas agregadas de pagos y cuotas del evento",
        responses={200: 'OK'},
        tags=["Eventos"]
    )
    @action(detail=True, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request, pk=None):
        evento = self.get_object()
        stats = SistemaPagosService.obtener_estadisticas_evento(evento)

        if not stats:
            return Response({'error': 'No hay estadísticas disponibles para este evento'}, status=404)

        # Normalizar montos (Decimal) a string para JSON
        montos = stats.get('montos', {})
        montos_serializados = {k: (str(v) if v is not None else None) for k, v in montos.items()}

        payload = {
            'evento': {
                'id': evento.id,
                'nombre': evento.nombre,
                'tipo': evento.tipo,
            },
            'estudiantes': stats.get('estudiantes', {}),
            'cuotas': stats.get('cuotas', {}),
            'montos': montos_serializados,
            'estudiantes_atrasados': stats.get('estudiantes_atrasados', []),
        }

        return Response(payload)


class CertificadoViewSet(viewsets.ModelViewSet):
    queryset = Certificado.objects.all()
    serializer_class = CertificadoSerializer

    @swagger_auto_schema(
        operation_description="Genera y retorna el PDF del certificado inline en el navegador (sin guardar en servidor)",
        responses={200: 'application/pdf'},
        tags=["Certificados"]
    )
    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        certificado = self.get_object()

        # Foto en bytes (opcional)
        foto_bytes = None
        try:
            if certificado.foto and certificado.foto.path and os.path.exists(certificado.foto.path):
                with open(certificado.foto.path, 'rb') as f:
                    foto_bytes = f.read()
        except Exception:
            foto_bytes = None

        # QR: usar existente o generar y persistir si falta
        qr_bytes = _ensure_qr_bytes_and_persist(certificado, request)

        pdf_bytes = generar_certificado_bytes(
            estudiante=certificado.estudiante,
            certificado=certificado,
            plantilla_path=certificado.evento.plantilla.path if certificado.evento.plantilla else None,
            foto_bytes=foto_bytes,
            qr_bytes=qr_bytes,
        )

        filename = f"{certificado.evento.aval}-SCI-{certificado.evento.codigo_evento}-{certificado.codigo_certificado}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @swagger_auto_schema(
        operation_description="Genera (o recupera) un certificado por estudiante y evento y retorna el PDF inline",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estudiante_id', 'evento_id'],
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'evento_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        responses={200: 'application/pdf'},
        tags=["Certificados"]
    )
    @action(detail=False, methods=['post'], url_path='generar_pdf')
    def generar_pdf(self, request):
        try:
            estudiante_id = int(request.data.get('estudiante_id'))
            evento_id = int(request.data.get('evento_id'))
        except Exception:
            return Response({'error': 'estudiante_id y evento_id son requeridos'}, status=400)

        try:
            estudiante = Estudiante.objects.get(id=estudiante_id)
            evento = Evento.objects.get(id=evento_id)
        except Estudiante.DoesNotExist:
            return Response({'error': 'Estudiante no encontrado'}, status=404)
        except Evento.DoesNotExist:
            return Response({'error': 'Evento no encontrado'}, status=404)

        # Buscar o crear certificado
        certificado, _ = Certificado.objects.get_or_create(
            estudiante=estudiante,
            evento=evento,
            defaults={'codigo_certificado': ''}  # el save() autogenera si está vacío
        )

        # Preparar bytes de imágenes
        foto_bytes = None
        if certificado.foto and getattr(certificado.foto, 'path', None) and os.path.exists(certificado.foto.path):
            with open(certificado.foto.path, 'rb') as f:
                foto_bytes = f.read()

        qr_bytes = _ensure_qr_bytes_and_persist(certificado, request)

        pdf_bytes = generar_certificado_bytes(
            estudiante=estudiante,
            certificado=certificado,
            plantilla_path=evento.plantilla.path if evento.plantilla else None,
            foto_bytes=foto_bytes,
            qr_bytes=qr_bytes,
        )

        filename = f"{evento.aval}-SCI-{evento.codigo_evento}-{certificado.codigo_certificado}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @swagger_auto_schema(
        operation_description="Genera certificado FINAL en PDF inline si cumple condiciones (pagos completados y certificado pagado si aplica)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estudiante_id', 'evento_id'],
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'evento_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={
            200: 'application/pdf',
            400: "No elegible: devuelve checklist de requisitos no cumplidos"
        },
        tags=["Certificados"]
    )
    @action(detail=False, methods=['post'], url_path='generar_final_pdf')
    def generar_final_pdf(self, request):
        try:
            estudiante_id = int(request.data.get('estudiante_id'))
            evento_id = int(request.data.get('evento_id'))
        except Exception:
            return Response({'error': 'estudiante_id y evento_id son requeridos'}, status=400)

        try:
            estudiante = Estudiante.objects.get(id=estudiante_id)
            evento = Evento.objects.get(id=evento_id)
        except Estudiante.DoesNotExist:
            return Response({'error': 'Estudiante no encontrado'}, status=404)
        except Evento.DoesNotExist:
            return Response({'error': 'Evento no encontrado'}, status=404)

        # Verificar elegibilidad usando el servicio de pagos
        resumen = SistemaPagosService.obtener_resumen_estudiante(estudiante, evento)
        estado_pagos = EstadoPagosEvento.objects.filter(estudiante=estudiante, evento=evento).first()

        checks = {
            'colegiatura_completada': False,
            'certificado_pagado': False,
            'matricula_pagada': False,
        }
        motivos = []

        if resumen and resumen.get('estado_general') == 'completado':
            checks['colegiatura_completada'] = True
        else:
            motivos.append('Colegiatura no está completamente pagada')

        # Certificado pagado solo si el evento tiene costo de certificado > 0
        if float(evento.costo_certificado or 0) <= 0:
            checks['certificado_pagado'] = True
        elif estado_pagos and estado_pagos.certificado_pagado:
            checks['certificado_pagado'] = True
        else:
            motivos.append('Pago de certificado pendiente')

        # Matrícula pagada si el evento la requiere
        if not evento.requiere_matricula:
            checks['matricula_pagada'] = True
        elif estado_pagos and estado_pagos.matricula_pagada:
            checks['matricula_pagada'] = True
        else:
            motivos.append('Pago de matrícula pendiente')

        if not all(checks.values()):
            return Response({
                'elegible': False,
                'motivos': motivos,
                'checks': checks
            }, status=400)

        # Elegible: generar/obtener certificado y devolver PDF inline
        certificado, _ = Certificado.objects.get_or_create(
            estudiante=estudiante,
            evento=evento,
            defaults={'codigo_certificado': ''}
        )

        # Foto (opcional)
        foto_bytes = None
        if certificado.foto and getattr(certificado.foto, 'path', None) and os.path.exists(certificado.foto.path):
            with open(certificado.foto.path, 'rb') as f:
                foto_bytes = f.read()

        # QR (existente o on-the-fly)
        qr_bytes = _ensure_qr_bytes_and_persist(certificado, request)

        pdf_bytes = generar_certificado_bytes(
            estudiante=estudiante,
            certificado=certificado,
            plantilla_path=evento.plantilla.path if evento.plantilla else None,
            foto_bytes=foto_bytes,
            qr_bytes=qr_bytes,
        )
        filename = f"{evento.aval}-SCI-{evento.codigo_evento}-{certificado.codigo_certificado}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @swagger_auto_schema(
        operation_description="Genera certificado de MATRÍCULA en PDF inline si tiene matrícula activa (y matrícula pagada si aplica)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estudiante_id', 'evento_id'],
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'evento_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={
            200: 'application/pdf',
            400: "No elegible: devuelve checklist de requisitos no cumplidos"
        },
        tags=["Certificados"]
    )
    @action(detail=False, methods=['post'], url_path='generar_matricula_pdf')
    def generar_matricula_pdf(self, request):
        try:
            estudiante_id = int(request.data.get('estudiante_id'))
            evento_id = int(request.data.get('evento_id'))
        except Exception:
            return Response({'error': 'estudiante_id y evento_id son requeridos'}, status=400)

        try:
            estudiante = Estudiante.objects.get(id=estudiante_id)
            evento = Evento.objects.get(id=evento_id)
        except Estudiante.DoesNotExist:
            return Response({'error': 'Estudiante no encontrado'}, status=404)
        except Evento.DoesNotExist:
            return Response({'error': 'Evento no encontrado'}, status=404)

        # Verificar existencia de matrícula
        matricula = Matricula.objects.filter(estudiante=estudiante, evento=evento).first()
        estado_pagos = EstadoPagosEvento.objects.filter(estudiante=estudiante, evento=evento).first()

        checks = {
            'tiene_matricula': bool(matricula),
            'matricula_activa_o_pendiente': bool(matricula and matricula.estado in ('activa', 'pendiente')),
            'matricula_pagada': False,
        }
        motivos = []

        if not checks['tiene_matricula']:
            motivos.append('No existe matrícula para este evento')
        if not checks['matricula_activa_o_pendiente']:
            motivos.append('La matrícula no está activa o está cancelada')

        if not evento.requiere_matricula:
            checks['matricula_pagada'] = True
        elif estado_pagos and estado_pagos.matricula_pagada:
            checks['matricula_pagada'] = True
        else:
            motivos.append('Pago de matrícula pendiente')

        if not all(checks.values()):
            return Response({
                'elegible': False,
                'motivos': motivos,
                'checks': checks
            }, status=400)

        # Elegible: crear/obtener certificado y enviar
        certificado, _ = Certificado.objects.get_or_create(
            estudiante=estudiante,
            evento=evento,
            defaults={'codigo_certificado': ''}
        )

        foto_bytes = None
        if certificado.foto and getattr(certificado.foto, 'path', None) and os.path.exists(certificado.foto.path):
            with open(certificado.foto.path, 'rb') as f:
                foto_bytes = f.read()

        qr_bytes = None
        if certificado.qr and getattr(certificado.qr, 'path', None) and os.path.exists(certificado.qr.path):
            with open(certificado.qr.path, 'rb') as f:
                qr_bytes = f.read()
        else:
            codigo = certificado.codigo_certificado
            validar_path = f"/api/v1/certificados/validar/?codigo={codigo}"
            payload = request.build_absolute_uri(validar_path)
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
            qr.add_data(payload)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_bytes = buffer.getvalue()

        pdf_bytes = generar_certificado_bytes(
            estudiante=estudiante,
            certificado=certificado,
            plantilla_path=evento.plantilla.path if evento.plantilla else None,
            foto_bytes=foto_bytes,
            qr_bytes=qr_bytes,
        )
        filename = f"CONSTANCIA-{evento.codigo_evento}-{certificado.codigo_certificado}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class ValidarCertificadoAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_description="Valida un certificado por su código",
        manual_parameters=[
            openapi.Parameter('codigo', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description='Código del certificado')
        ],
        responses={200: 'OK'},
        tags=["Certificados"]
    )
    def get(self, request, *args, **kwargs):
        codigo = request.GET.get('codigo')
        if not codigo:
            return JsonResponse({'valido': False, 'error': 'codigo requerido'}, status=400)

        cert = Certificado.objects.filter(codigo_certificado=codigo).select_related('estudiante', 'evento').first()
        if not cert:
            return JsonResponse({'valido': False})

        data = {
            'valido': True,
            'codigo': cert.codigo_certificado,
            'estudiante': {
                'id': cert.estudiante.id,
                'nombres': cert.estudiante.nombres,
                'apellidos': cert.estudiante.apellidos,
                'cedula': cert.estudiante.cedula,
            },
            'evento': {
                'id': cert.evento.id,
                'nombre': cert.evento.nombre,
                'tipo': cert.evento.tipo,
                'horas_academicas': cert.evento.horas_academicas,
                'fecha_inicio': cert.evento.fecha_inicio,
                'fecha_fin': cert.evento.fecha_fin,
            },
            'fecha_emision': cert.fecha_emision,
            'estado': cert.estado,
        }
        return JsonResponse(data)


class CertificadoPDFPublicAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_description="Devuelve el PDF inline de un certificado a partir de su código",
        manual_parameters=[
            openapi.Parameter('codigo', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description='Código del certificado')
        ],
        responses={200: 'application/pdf'},
        tags=["Certificados"]
    )
    def get(self, request, *args, **kwargs):
        codigo = request.GET.get('codigo')
        if not codigo:
            return JsonResponse({'error': 'codigo requerido'}, status=400)

        cert = Certificado.objects.filter(codigo_certificado=codigo).select_related('estudiante', 'evento').first()
        if not cert:
            return JsonResponse({'error': 'certificado no encontrado'}, status=404)

        # Foto
        foto_bytes = None
        try:
            if cert.foto and getattr(cert.foto, 'path', None) and os.path.exists(cert.foto.path):
                with open(cert.foto.path, 'rb') as f:
                    foto_bytes = f.read()
        except Exception:
            pass

        # QR (persistente/generado)
        qr_bytes = _ensure_qr_bytes_and_persist(cert, request)

        pdf_bytes = generar_certificado_bytes(
            estudiante=cert.estudiante,
            certificado=cert,
            plantilla_path=cert.evento.plantilla.path if cert.evento.plantilla else None,
            foto_bytes=foto_bytes,
            qr_bytes=qr_bytes,
        )
        filename = f"{cert.evento.aval}-SCI-{cert.evento.codigo_evento}-{cert.codigo_certificado}.pdf"
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{filename}"'
        return resp


class ConstanciaPublicAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_description="Muestra una pagina HTML simple con visor de constancia y descarga",
        manual_parameters=[
            openapi.Parameter('codigo', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description='Codigo de certificado')
        ],
        tags=["Certificados"]
    )
    def get(self, request, *args, **kwargs):
        codigo = request.GET.get('codigo')
        if not codigo:
            return HttpResponse('codigo requerido', status=400)

        cert = Certificado.objects.filter(codigo_certificado=codigo).select_related('estudiante', 'evento').first()
        if not cert:
            return HttpResponse('certificado no encontrado', status=404)

        # Generar constancia en memoria
        qr_bytes = _ensure_qr_bytes_and_persist(cert, request)
        pdf_bytes = generar_constancia_bytes(cert.estudiante, cert, cert.evento, qr_bytes)

        # HTML simple con <embed>
        from base64 import b64encode
        b64 = b64encode(pdf_bytes).decode('utf-8')
        html = f"""
<!doctype html>
<html><head><meta charset='utf-8'>
<title>Constancia {codigo}</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>body{{margin:0;font-family:system-ui,Arial}}header{{padding:12px 16px;border-bottom:1px solid #ddd}}main{{height:calc(100vh - 52px)}}embed,iframe{{width:100%;height:100%;border:0}}</style>
</head>
<body>
<header>
  <strong>Constancia</strong> — Codigo: {codigo} — {cert.estudiante.nombres} {cert.estudiante.apellidos}
  <span style='float:right'><a download='constancia_{codigo}.pdf' href='data:application/pdf;base64,{b64}'>Descargar PDF</a></span>
</header>
<main>
  <embed type='application/pdf' src='data:application/pdf;base64,{b64}' />
</main>
</body></html>
"""
        return HttpResponse(html)


class ExportarCertificadosZipAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Genera un ZIP con certificados PDF para los estudiantes seleccionados",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['evento_id', 'tipo'],
            properties={
                'evento_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'tipo': openapi.Schema(type=openapi.TYPE_STRING, enum=['final', 'matricula']),
                'estudiante_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER)),
                'omitir_no_elegibles': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                'limite': openapi.Schema(type=openapi.TYPE_INTEGER, description='Máximo de certificados a incluir', default=500),
            }
        ),
        responses={200: 'application/zip'},
        tags=["Certificados"]
    )
    def post(self, request, *args, **kwargs):
        from django.http import FileResponse
        data = request.data
        try:
            evento_id = int(data.get('evento_id'))
        except Exception:
            return Response({'error': 'evento_id requerido'}, status=400)

        tipo = (data.get('tipo') or '').strip()
        if tipo not in ('final', 'matricula'):
            return Response({'error': "tipo debe ser 'final' o 'matricula'"}, status=400)

        try:
            evento = Evento.objects.get(id=evento_id)
        except Evento.DoesNotExist:
            return Response({'error': 'Evento no encontrado'}, status=404)

        estudiante_ids = data.get('estudiante_ids') or []
        if estudiante_ids and not isinstance(estudiante_ids, list):
            return Response({'error': 'estudiante_ids debe ser una lista de IDs'}, status=400)

        # Selección base
        if estudiante_ids:
            estudiantes = Estudiante.objects.filter(id__in=estudiante_ids)
        else:
            # Si no se especifica, por defecto todos vinculados al evento por M2M o matrícula
            from django.db.models import Q
            estudiantes = Estudiante.objects.filter(Q(eventos_matriculados=evento) | Q(matriculas__evento=evento)).distinct()

        limite = int(data.get('limite') or 500)
        if estudiantes.count() > limite:
            return Response({'error': f'Demasiados certificados ({estudiantes.count()}). Límite {limite}. Filtra o provee estudiante_ids.'}, status=400)

        omitir_no_elegibles = bool(data.get('omitir_no_elegibles', True))

        # Helpers de elegibilidad
        def elegible_final(est, ev):
            resumen = SistemaPagosService.obtener_resumen_estudiante(est, ev)
            estado_pagos = EstadoPagosEvento.objects.filter(estudiante=est, evento=ev).first()
            if not (resumen and resumen.get('estado_general') == 'completado'):
                return False, 'colegiatura_incompleta'
            if float(ev.costo_certificado or 0) > 0 and not (estado_pagos and estado_pagos.certificado_pagado):
                return False, 'certificado_no_pagado'
            if ev.requiere_matricula and not (estado_pagos and estado_pagos.matricula_pagada):
                return False, 'matricula_no_pagada'
            return True, None

        def elegible_matricula(est, ev):
            m = Matricula.objects.filter(estudiante=est, evento=ev).first()
            if not m:
                return False, 'sin_matricula'
            if ev.requiere_matricula:
                ep = EstadoPagosEvento.objects.filter(estudiante=est, evento=ev).first()
                if not (ep and ep.matricula_pagada):
                    return False, 'matricula_no_pagada'
            return True, None

        # Crear ZIP temporal
        import tempfile, zipfile
        tmp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        resumen_zip = {
            'evento': {
                'id': evento.id,
                'codigo_evento': evento.codigo_evento,
                'nombre': evento.nombre,
            },
            'tipo': tipo,
            'generado_en': dt.datetime.utcnow().isoformat() + 'Z',
            'incluidos': [],
            'omitidos': [],
            'total_solicitados': estudiantes.count(),
        }

        with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            carpeta = evento.codigo_evento or f'evento_{evento.id}'
            for est in estudiantes:
                ok = False
                razon = None
                if tipo == 'final':
                    ok, razon = elegible_final(est, evento)
                else:
                    ok, razon = elegible_matricula(est, evento)

                if not ok:
                    if not omitir_no_elegibles:
                        # Aún así incluir un TXT indicando la causa
                        nota = f"Estudiante {est.id} no elegible: {razon}\n"
                        zf.writestr(f"{carpeta}/NO_ELEGIBLE_{est.id}.txt", nota)
                    resumen_zip['omitidos'].append({'estudiante_id': est.id, 'razon': razon})
                    continue

                # Obtener/crear certificado y PDF bytes
                cert, _ = Certificado.objects.get_or_create(estudiante=est, evento=evento, defaults={'codigo_certificado': ''})
                # Foto opcional
                foto_bytes = None
                try:
                    if cert.foto and getattr(cert.foto, 'path', None) and os.path.exists(cert.foto.path):
                        with open(cert.foto.path, 'rb') as f:
                            foto_bytes = f.read()
                except Exception:
                    pass

                qr_bytes = _ensure_qr_bytes_and_persist(cert, request)
                pdf_bytes = generar_certificado_bytes(
                    estudiante=est,
                    certificado=cert,
                    plantilla_path=evento.plantilla.path if evento.plantilla else None,
                    foto_bytes=foto_bytes,
                    qr_bytes=qr_bytes,
                )

                filename = f"{evento.aval}-SCI-{evento.codigo_evento}-{cert.codigo_certificado}.pdf"
                arcname = f"{carpeta}/{filename}"
                zf.writestr(arcname, pdf_bytes)
                resumen_zip['incluidos'].append({'estudiante_id': est.id, 'certificado': cert.codigo_certificado, 'archivo': arcname})

            # Agregar resumen.json
            zf.writestr(f"{carpeta}/resumen.json", json.dumps(resumen_zip, ensure_ascii=False, indent=2))

        tmp_zip.flush()
        tmp_zip.seek(0)

        fecha = dt.date.today().isoformat()
        zip_name = f"certificados_{evento.codigo_evento}_{tipo}_{fecha}.zip"
        response = FileResponse(open(tmp_zip.name, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_name}"'
        return response


class GenerarCertificadosDesdeCSVAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Carga masiva de certificados desde un ZIP y genera los certificados",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True, description='Archivo ZIP'),
            openapi.Parameter('evento_id', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=True, description='ID del evento')
        ],
        responses={200: 'OK'},
        tags=["Carga Masiva Certificados"]
    )
    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'Archivo ZIP no encontrado'}, status=400)

        evento_id = request.POST.get('evento_id')
        if not evento_id:
            return JsonResponse({'error': 'Debe proporcionar evento_id'}, status=400)

        try:
            evento = Evento.objects.get(id=evento_id)
        except Evento.DoesNotExist:
            return JsonResponse({'error': 'Evento no encontrado'}, status=404)

        import zipfile
        import tempfile

        uploaded_zip = request.FILES['file']
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'uploaded.zip')
            with open(zip_path, 'wb+') as f:
                for chunk in uploaded_zip.chunks():
                    f.write(chunk)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            csv_path = os.path.join(temp_dir, 'data.csv')
            if not os.path.exists(csv_path):
                return JsonResponse({'error': 'No se encontró data.csv en el archivo ZIP'}, status=400)

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f.readlines())
                resultados = []
                errores = []

                for row in reader:
                    try:
                        cedula = row['cedula'].strip()
                        nombre_completo = row['nombres'].strip()
                        nombres, *apellidos_restantes = nombre_completo.split()
                        apellidos = ' '.join(apellidos_restantes) if apellidos_restantes else '---'
                        correo = f"{cedula}@noemail.com"
                        qr_path = os.path.normpath(os.path.join(temp_dir, row['qr']))
                        foto_path = os.path.normpath(os.path.join(temp_dir, row['ruta']))
                        codigo_certificado = row['Codigo'].strip()

                        estudiante, _ = Estudiante.objects.get_or_create(
                            cedula=cedula,
                            defaults={
                                'nombres': nombres,
                                'apellidos': apellidos,
                                'correo': correo,
                                'ciudad': 'Importada',
                                'codigo_estudiante': f"EST-{uuid_lib.uuid4().hex[:8]}"
                            }
                        )

                        estudiante.eventos_matriculados.add(evento)
                        estudiante.save()

                        certificado, creado = Certificado.objects.get_or_create(
                            estudiante=estudiante,
                            evento=evento,
                            defaults={'codigo_certificado': codigo_certificado}
                        )

                        if creado:
                            if os.path.exists(qr_path):
                                with open(qr_path, 'rb') as f:
                                    certificado.qr.save(os.path.basename(qr_path), File(f), save=True)
                            if os.path.exists(foto_path):
                                with open(foto_path, 'rb') as f:
                                    certificado.foto.save(os.path.basename(foto_path), File(f), save=True)

                            ruta_qr = certificado.qr.path
                            ruta_foto = certificado.foto.path
                            output_path = generar_certificado(estudiante, certificado, ruta_foto, ruta_qr)

                            #with open(output_path, 'rb') as f:
                            #    certificado.archivo_pdf.save(os.path.join(certificado.evento.codigo_evento, f"{codigo_certificado}.pdf"), File(f), save=True)

                            resultados.append({
                                'estudiante': f"{estudiante.nombres} {estudiante.apellidos}",
                                'codigo_certificado': certificado.codigo_certificado
                            })
                        else:
                            errores.append({
                                'codigo_certificado': codigo_certificado,
                                'error': 'Ya existe un certificado con este código.'
                            })
                    except Exception as e:
                        errores.append({'row': row, 'error': str(e)})

            return JsonResponse({'estado': 'completado', 'creados': resultados, 'errores': errores})

from django.db.models.signals import post_delete
from django.dispatch import receiver

@receiver(post_delete, sender=Certificado)
def eliminar_archivos_certificado(sender, instance, **kwargs):
    if instance.qr and instance.qr.path and os.path.exists(instance.qr.path):
        os.remove(instance.qr.path)
    if instance.foto and instance.foto.path and os.path.exists(instance.foto.path):
        os.remove(instance.foto.path)
    if instance.archivo_pdf and instance.archivo_pdf.path and os.path.exists(instance.archivo_pdf.path):
        os.remove(instance.archivo_pdf.path)
