from django.db import models
from modulos.modulo_estudiantes.models import Estudiante
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

ESTADO_CERTIFICADO = [
    ('PENDIENTE', 'Pendiente'),
    ('GENERADO', 'Generado'),
    ('ENTREGADO', 'Entregado'),
    ('ANULADO', 'Anulado'),
]

class Evento(models.Model):
    TIPO_CERTIFICADO_CHOICES = [
        ('diploma', 'Diploma'),
        ('vinculacion', 'Vinculación'),
        ('simposio', 'Simposio'),
        ('conversatorio', 'Conversatorio'),
    ]

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPO_CERTIFICADO_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()   
    lugar = models.CharField(max_length=150, blank=True)
    codigo_evento = models.CharField(max_length=20, unique=True, default='TEMP_EVT')
    aval = models.CharField(max_length=20, blank=True, default='UTEQ')
    horas_academicas = models.IntegerField(default=20)
    plantilla = models.ImageField(upload_to='plantillas/', blank=True, null=True)

    # Campos de costos
    costo_matricula = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=0
    )
    costo_colegiatura = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=0
    )
    costo_certificado = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=0
    )

    # Configuración de pagos (quitamos numero_maximo_cuotas; se define por PlanPago)
    requiere_matricula = models.BooleanField(default=True)
    permite_pago_certificado_anticipado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - {self.tipo}"

    @property
    def costo_total(self):
        return self.costo_matricula + self.costo_colegiatura + self.costo_certificado

class CostoMiscelaneo(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='costos_miscelaneos')
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    es_obligatorio = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descripcion} - {self.evento.nombre}"



class Certificado(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    codigo_certificado = models.CharField(max_length=50, unique=True, blank=True)
    fecha_emision = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CERTIFICADO, default='PENDIENTE')
    archivo_pdf = models.FileField(upload_to='certificados/', blank=True, null=True)
    generado_en = models.DateTimeField(auto_now_add=True)
    foto = models.ImageField(upload_to='fotos_estudiantes/', blank=True, null=True)
    qr = models.ImageField(upload_to='qr_certificados/', blank=True, null=True)
    pagado = models.BooleanField(default=False)
 
    @property
    def horas_evento(self):
        return self.evento.horas_academicas

    def save(self, *args, **kwargs):
        if not self.codigo_certificado:
            base_code = f"{self.evento.codigo_evento}-{self.estudiante.codigo_estudiante}"
            counter = 1
            temp_code = base_code
            while Certificado.objects.filter(codigo_certificado=temp_code).exists():
                temp_code = f"{base_code}-{counter}"
                counter += 1
            self.codigo_certificado = temp_code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_certificado} - {self.estudiante}"
