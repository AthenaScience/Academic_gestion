from django.db import models

class Estudiante(models.Model):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(unique=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ciudad = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    foto = models.ImageField(upload_to='fotos_estudiantes/', blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    direccion_2 = models.CharField(max_length=255, blank=True, null=True, default='')
    pais = models.CharField(max_length=100, blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    codigo_estudiante = models.CharField(max_length=20, unique=True, default='TEMP_EST')
    fecha_modificacion = models.DateTimeField(auto_now=True)
    eventos_matriculados = models.ManyToManyField('modulo_certificados.Evento', blank=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.cedula})"
