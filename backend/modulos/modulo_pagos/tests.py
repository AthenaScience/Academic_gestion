from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento
from modulos.modulo_pagos.models import (
    PlanPago,
    Cuota,
    Beca,
    Descuento,
)


class PagosModelsTest(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        User.objects.create_user(
            username="tester", password="tester", is_staff=True, is_superuser=True
        )

        self.evento = Evento.objects.create(
            nombre="Evento Pagos Unit",
            tipo="diploma",
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=60),
            lugar="UTEQ",
            codigo_evento="EVT-PAG-UNIT",
            aval="UTEQ",
            horas_academicas=120,
            costo_matricula=Decimal("50.00"),
            costo_colegiatura=Decimal("300.00"),
            costo_certificado=Decimal("25.00"),
            # numero_maximo_cuotas eliminado
        )
        self.estudiante = Estudiante.objects.create(
            nombres="Pedro",
            apellidos="Pago",
            cedula="1231231239",
            correo="pedro.pago@example.com",
            ciudad="Quito",
            codigo_estudiante="EST-PAG-UNIT",
        )

    def test_plan_unico_generar_cuotas(self):
        plan = PlanPago.objects.create(
            estudiante=self.estudiante,
            evento=self.evento,
            numero_cuotas=5,
            monto_colegiatura=Decimal("250.00"),
            usa_monto_personalizado=True,
        )

        cuotas = plan.generar_cuotas()
        self.assertEqual(len(cuotas), 5)
        self.assertEqual(plan.cuotas.count(), 5)
        first = plan.cuotas.order_by("numero_cuota").first()
        self.assertEqual(first.estado, "pendiente")

    def test_beca_porcentual_y_descuento_monto_fijo(self):
        # Beca porcentual 10% para colegiatura
        beca = Beca.objects.create(
            estudiante=self.estudiante,
            evento=self.evento,
            nombre_beca="Excelencia",
            tipo_beca="porcentual",
            porcentaje_descuento=Decimal("10.00"),
            aplica_matricula=False,
            aplica_colegiatura=True,
            aplica_certificado=False,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=10),
            estado="activa",
            motivo="Alto rendimiento",
        )
        dcto = Descuento.objects.create(
            estudiante=self.estudiante,
            evento=self.evento,
            nombre_descuento="Promo",
            tipo_descuento="monto_fijo",
            monto_descuento=Decimal("15.00"),
            aplica_matricula=True,
            aplica_colegiatura=False,
            aplica_certificado=False,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=10),
            estado="activo",
            motivo="Promoción",
        )

        # Beca 10% de 300 = 30
        beca_desc = beca.calcular_descuento(Decimal("300.00"), "colegiatura")
        self.assertEqual(beca_desc, Decimal("30.00"))

        # Descuento monto fijo 15 sobre matrícula 50 = 15
        dcto_monto = dcto.calcular_descuento(Decimal("50.00"), "matricula")
        self.assertEqual(dcto_monto, Decimal("15.00"))


