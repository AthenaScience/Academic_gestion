from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento
from modulos.modulo_pagos.models import (
    PlanPago,
    Matricula,
    Cuota,
    Pago,
    EstadoPagosEvento,
)


class TestAPIPagosEndpoints(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(
            username="tester", password="tester", is_staff=True, is_superuser=True
        )
        self.client = APIClient()
        r = self.client.post(
            "/api/v1/auth/jwt/", {"username": "tester", "password": "tester"}, format="json"
        )
        assert r.status_code == 200
        token = r.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        hoy = date.today()
        self.evento = Evento.objects.create(
            nombre="Evento Pagos",
            tipo="diploma",
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            lugar="UTEQ",
            codigo_evento="EVT-PAG-TEST",
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
            nombres="Pablo",
            apellidos="Pagador",
            cedula="7775554442",
            correo="pablo.pagador@example.com",
            ciudad="Guayaquil",
            codigo_estudiante="EST-PAG-1",
        )

        self.plan = PlanPago.objects.create(
            estudiante=self.estudiante,
            evento=self.evento,
            monto_colegiatura=Decimal("100.00"),
            numero_cuotas=1,
        )
        self.matricula = Matricula.objects.create(
            estudiante=self.estudiante, evento=self.evento, plan_pago=self.plan, estado="activa"
        )
        self.cuota = Cuota.objects.create(
            plan_pago=self.plan,
            numero_cuota=1,
            monto=Decimal("100.00"),
            fecha_vencimiento=hoy + timedelta(days=15),
            estado="pendiente",
        )
        EstadoPagosEvento.objects.get_or_create(estudiante=self.estudiante, evento=self.evento)

    def test_crear_pago_matricula_y_cuota_y_certificado(self):
        # pago matrícula
        r = self.client.post(
            f"/api/v1/matriculas/{self.matricula.id}/registrar_pago_matricula/",
            {"metodo_pago": "efectivo"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)

        # pago cuota
        r = self.client.post(
            f"/api/v1/estudiantes/{self.estudiante.id}/registrar_pago/",
            {
                "tipo_pago": "cuota_individual",
                "evento": self.evento.id,
                "cuota": self.cuota.id,
                "monto": "100.00",
                "metodo_pago": "efectivo",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)

        # pago certificado
        r = self.client.post(
            f"/api/v1/estudiantes/{self.estudiante.id}/registrar_pago/",
            {
                "tipo_pago": "certificado",
                "evento": self.evento.id,
                "monto": "25.00",
                "metodo_pago": "efectivo",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)

    def test_filtros_pagos(self):
        # crear un pago simple
        Pago.objects.create(
            estudiante=self.estudiante,
            evento=self.evento,
            tipo_pago="otro",
            monto=Decimal("10.00"),
            metodo_pago="efectivo",
        )
        # filtros
        r = self.client.get(f"/api/v1/pagos/?estudiante={self.estudiante.id}")
        self.assertEqual(r.status_code, 200)
        r = self.client.get(f"/api/v1/pagos/por_estudiante/?estudiante_id={self.estudiante.id}")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/api/v1/pagos/por_tipo/?tipo=otro")
        self.assertEqual(r.status_code, 200)

