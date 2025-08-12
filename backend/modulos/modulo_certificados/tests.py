from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from modulos.modulo_certificados.models import Evento, Certificado
from modulos.modulo_estudiantes.models import Estudiante


class CertificadosModelsTest(TestCase):
    def setUp(self) -> None:
        # Usuario admin para coherencia en entornos que lo requieran
        User = get_user_model()
        User.objects.create_user(
            username="tester", password="tester", is_staff=True, is_superuser=True
        )

        self.evento = Evento.objects.create(
            nombre="Evento Unit",
            tipo="diploma",
            fecha_inicio=date.today(),
            fecha_fin=date.today(),
            lugar="UTEQ",
            codigo_evento="EVT-UNIT",
            aval="UTEQ",
            horas_academicas=100,
            costo_matricula=Decimal("10.00"),
            costo_colegiatura=Decimal("20.00"),
            costo_certificado=Decimal("30.00"),
            # numero_maximo_cuotas eliminado
        )
        self.estudiante = Estudiante.objects.create(
            nombres="María",
            apellidos="Unitaria",
            cedula="1112223334",
            correo="maria.unitaria@example.com",
            ciudad="Quevedo",
            codigo_estudiante="EST-UNIT-01",
        )

    def test_evento_costo_total(self):
        self.assertEqual(self.evento.costo_total, Decimal("60.00"))

    def test_certificado_codigo_generado_automaticamente_y_unico(self):
        # Primer certificado: usa base EVT-UNIT-EST-UNIT-01
        c1 = Certificado.objects.create(evento=self.evento, estudiante=self.estudiante)
        self.assertTrue(c1.codigo_certificado.startswith("EVT-UNIT-EST-UNIT-01"))

        # Segundo certificado mismo par: debe desambiguar con sufijo -1
        c2 = Certificado.objects.create(evento=self.evento, estudiante=self.estudiante)
        self.assertTrue(c2.codigo_certificado.startswith("EVT-UNIT-EST-UNIT-01-"))
        self.assertNotEqual(c1.codigo_certificado, c2.codigo_certificado)


