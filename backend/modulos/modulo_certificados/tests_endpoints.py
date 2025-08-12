from datetime import date, timedelta
from decimal import Decimal
import io
import json
import zipfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento
from modulos.modulo_pagos.models import (
    PlanPago,
    Matricula,
    Cuota,
    EstadoPagosEvento,
)


class TestAPICertificadosEndpoints(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(
            username="tester", password="tester", is_staff=True, is_superuser=True
        )
        self.client = APIClient()
        resp = self.client.post(
            "/api/v1/auth/jwt/", {"username": "tester", "password": "tester"}, format="json"
        )
        assert resp.status_code == 200
        token = resp.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Datos base
        hoy = date.today()
        self.evento = Evento.objects.create(
            nombre="Evento Demo",
            tipo="diploma",
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            lugar="UTEQ",
            codigo_evento="EVT-DEMO-TEST",
            aval="UTEQ",
            horas_academicas=120,
            costo_matricula=Decimal("50.00"),
            costo_colegiatura=Decimal("100.00"),
            costo_certificado=Decimal("25.00"),

            requiere_matricula=True,
            permite_pago_certificado_anticipado=True,
        )
        self.estudiante = Estudiante.objects.create(
            nombres="Ana",
            apellidos="Prueba",
            cedula="9990001112",
            correo="ana.prueba@example.com",
            ciudad="Quevedo",
            codigo_estudiante="EST-TEST-1",
        )

    def _preparar_plan_pagado_completo(self):
        # Matricular estudiante en el evento usando M2M (esto dispara señales que crean objetos automáticamente)
        self.estudiante.eventos_matriculados.add(self.evento)
        
        # Obtener o crear objetos que podrían haber sido creados por señales
        plan = PlanPago.objects.filter(estudiante=self.estudiante, evento=self.evento).first()
        if not plan:
            plan = PlanPago.objects.create(
                estudiante=self.estudiante, 
                evento=self.evento,
                monto_colegiatura=Decimal("100.00"), 
                numero_cuotas=1
            )
        
        matricula = Matricula.objects.filter(estudiante=self.estudiante, evento=self.evento).first()
        if not matricula:
            matricula = Matricula.objects.create(
                estudiante=self.estudiante, 
                evento=self.evento,
                plan_pago=plan, 
                estado='activa'
            )
        
        # Trabajar con cuotas existentes o crear si no existen
        cuotas = Cuota.objects.filter(plan_pago=plan)
        if cuotas.exists():
            # Marcar todas las cuotas como pagadas completamente
            for cuota in cuotas:
                cuota.estado = "pagado"  # Estado correcto según el modelo
                cuota.monto_pagado = cuota.monto  # Importante: monto pagado = monto total
                cuota.fecha_pago = date.today()  # Agregar fecha de pago
                cuota.save()
            cuota = cuotas.first()
        else:
            # Crear cuota manualmente si no hay
            cuota = Cuota.objects.create(
                plan_pago=plan,
                numero_cuota=1,
                monto=Decimal("100.00"),
                fecha_vencimiento=date.today(),
                estado="pagado",
                monto_pagado=Decimal("100.00"),
                fecha_pago=date.today(),
            )
        
        # Configurar estado de pagos
        ep, _ = EstadoPagosEvento.objects.get_or_create(estudiante=self.estudiante, evento=self.evento)
        ep.matricula_pagada = True
        ep.colegiatura_al_dia = True
        ep.certificado_pagado = True
        ep.save()
        
        # Forzar actualización del estado de colegiatura verificando todas las cuotas están pagadas
        cuotas_pendientes = Cuota.objects.filter(plan_pago=plan, estado='pendiente').exists()
        if not cuotas_pendientes:
            ep.colegiatura_al_dia = True
            ep.save()
        
        return plan, cuota

    def test_generar_final_pdf(self):
        self._preparar_plan_pagado_completo()
        resp = self.client.post(
            "/api/v1/certificados/generar_final_pdf/",
            {"estudiante_id": self.estudiante.id, "evento_id": self.evento.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp["Content-Type"].startswith("application/pdf"))
        self.assertGreater(len(resp.content), 10_000)

    def test_generar_matricula_pdf(self):
        # Matricular estudiante en el evento usando M2M
        self.estudiante.eventos_matriculados.add(self.evento)
        
        # Obtener objetos que podrían haber sido creados por señales
        plan = PlanPago.objects.filter(estudiante=self.estudiante, evento=self.evento).first()
        if not plan:
            plan = PlanPago.objects.create(
                estudiante=self.estudiante, 
                evento=self.evento,
                monto_colegiatura=Decimal("100.00"), 
                numero_cuotas=1
            )
        
        matricula = Matricula.objects.filter(estudiante=self.estudiante, evento=self.evento).first()
        if not matricula:
            matricula = Matricula.objects.create(
                estudiante=self.estudiante, 
                evento=self.evento,
                plan_pago=plan, 
                estado='activa'
            )
        
        ep, _ = EstadoPagosEvento.objects.get_or_create(estudiante=self.estudiante, evento=self.evento)
        ep.matricula_pagada = True
        ep.save()

        resp = self.client.post(
            "/api/v1/certificados/generar_matricula_pdf/",
            {"estudiante_id": self.estudiante.id, "evento_id": self.evento.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp["Content-Type"].startswith("application/pdf"))

    def test_constancia_publica_html(self):
        self._preparar_plan_pagado_completo()
        r = self.client.post(
            "/api/v1/certificados/generar_final_pdf/",
            {"estudiante_id": self.estudiante.id, "evento_id": self.evento.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        lst = self.client.get("/api/v1/certificados/")
        codigo = lst.json()[-1]["codigo_certificado"]
        client_public = APIClient()
        r_html = client_public.get(f"/api/v1/certificados/constancia/?codigo={codigo}")
        self.assertEqual(r_html.status_code, 200)
        self.assertIn("text/html", r_html["Content-Type"])  # landing

    def test_exportar_zip(self):
        self._preparar_plan_pagado_completo()
        resp = self.client.post(
            "/api/v1/certificados/exportar_zip/",
            {"evento_id": self.evento.id, "tipo": "final", "estudiante_ids": [self.estudiante.id]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/zip", resp["Content-Type"])  # ZIP
        # FileResponse: usar streaming_content
        data = b"".join(resp.streaming_content)
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        self.assertTrue(any(name.endswith(".pdf") for name in names))
        self.assertTrue(any(name.endswith("resumen.json") for name in names))
        resumen = json.loads(zf.read([n for n in names if n.endswith("resumen.json")][0]).decode("utf-8"))
        self.assertEqual(resumen["tipo"], "final")
        self.assertTrue(resumen["incluidos"])

