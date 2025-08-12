from datetime import date, timedelta
from decimal import Decimal
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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


class TestAPIEstudiantesEndpoints(TestCase):
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

        # Base: evento + estudiante
        hoy = date.today()
        self.evento = Evento.objects.create(
            nombre="Evento Demo",
            tipo="diploma",
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            lugar="UTEQ",
            codigo_evento="EVT-ALUM-TEST",
            aval="UTEQ",
            horas_academicas=120,
            costo_matricula=Decimal("50.00"),
            costo_colegiatura=Decimal("100.00"),
            costo_certificado=Decimal("25.00"),
            # numero_maximo_cuotas eliminado
            requiere_matricula=True,
            permite_pago_certificado_anticipado=True,
        )
        self.estudiante = Estudiante.objects.create(
            nombres="Luis",
            apellidos="Tester",
            cedula="8887776665",
            correo="luis.tester@example.com",
            ciudad="Quito",
            codigo_estudiante="EST-ALUM-1",
        )

    def test_crud_basico_estudiantes(self):
        # List
        r = self.client.get("/api/v1/estudiantes/")
        self.assertEqual(r.status_code, 200)
        # Retrieve
        r = self.client.get(f"/api/v1/estudiantes/{self.estudiante.id}/")
        self.assertEqual(r.status_code, 200)
        # Update
        r = self.client.patch(
            f"/api/v1/estudiantes/{self.estudiante.id}/",
            {"telefono": "0999999999"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_acciones_estudiante(self):
        # Preparar plan + matricula + cuota pendiente
        plan = PlanPago.objects.create(
            estudiante=self.estudiante,
            evento=self.evento,
            monto_colegiatura=Decimal("100.00"),
            numero_cuotas=1,
        )
        Matricula.objects.create(
            estudiante=self.estudiante, evento=self.evento, plan_pago=plan, estado="activa"
        )
        Cuota.objects.create(
            plan_pago=plan,
            numero_cuota=1,
            monto=Decimal("100.00"),
            fecha_vencimiento=date.today() + timedelta(days=10),
            estado="pendiente",
        )
        EstadoPagosEvento.objects.get_or_create(estudiante=self.estudiante, evento=self.evento)

        # pagos (resumen)
        r = self.client.get(f"/api/v1/estudiantes/{self.estudiante.id}/pagos/")
        self.assertEqual(r.status_code, 200)
        # historial_pagos
        r = self.client.get(f"/api/v1/estudiantes/{self.estudiante.id}/historial_pagos/")
        self.assertEqual(r.status_code, 200)
        # cuotas_pendientes
        r = self.client.get(f"/api/v1/estudiantes/{self.estudiante.id}/cuotas_pendientes/")
        self.assertEqual(r.status_code, 200)
        # matriculas_activas
        r = self.client.get(f"/api/v1/estudiantes/{self.estudiante.id}/matriculas_activas/")
        self.assertEqual(r.status_code, 200)

    def test_carga_masiva_csv(self):
        csv_content = (
            "nombres,codigo_evento,cedula,correo,ciudad,telefono\n"
            "Carlos Quispe,%s,7775554443,carlos@example.com,Cuenca,0991112223\n" % self.evento.codigo_evento
        ).encode("utf-8")
        file = SimpleUploadedFile("estudiantes.csv", csv_content, content_type="text/csv")
        r = self.client.post(
            "/api/v1/estudiantes/cargar-estudiantes/",
            {"file": file},
            format="multipart",
        )
        self.assertEqual(r.status_code, 200)

