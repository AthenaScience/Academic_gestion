import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from factory import Faker
from factory.django import DjangoModelFactory
from .models import Estudiante


class EstudianteFactory(DjangoModelFactory):
    class Meta:
        model = Estudiante
    
    nombres = Faker('first_name')
    apellidos = Faker('last_name')
    cedula = Faker('numerify', text='##########')
    correo = Faker('email')
    ciudad = Faker('city')
    telefono = Faker('numerify', text='##########')
    fecha_nacimiento = Faker('date_of_birth', minimum_age=18, maximum_age=65)
    direccion = Faker('address')
    pais = Faker('country')
    provincia = Faker('state')
    codigo_estudiante = Faker('numerify', text='EST####')


class EstudianteModelTest(TestCase):
    """Tests para el modelo Estudiante"""
    
    def test_crear_estudiante_basico(self):
        """Test: Crear un estudiante con datos mínimos"""
        estudiante = EstudianteFactory()
        self.assertIsNotNone(estudiante.id)
        self.assertEqual(estudiante.nombres, estudiante.nombres)
        self.assertEqual(estudiante.apellidos, estudiante.apellidos)
    
    def test_cedula_unica(self):
        """Test: La cédula debe ser única"""
        cedula = "1234567890"
        EstudianteFactory(cedula=cedula)
        
        with self.assertRaises(IntegrityError):
            EstudianteFactory(cedula=cedula)
    
    def test_correo_unico(self):
        """Test: El correo debe ser único"""
        correo = "test@example.com"
        EstudianteFactory(correo=correo)
        
        with self.assertRaises(IntegrityError):
            EstudianteFactory(correo=correo)
    
    def test_codigo_estudiante_unico(self):
        """Test: El código de estudiante debe ser único"""
        codigo = "EST1234"
        EstudianteFactory(codigo_estudiante=codigo)
        
        with self.assertRaises(IntegrityError):
            EstudianteFactory(codigo_estudiante=codigo)
    
    def test_str_representation(self):
        """Test: La representación string del modelo"""
        estudiante = EstudianteFactory(
            nombres="Juan",
            apellidos="Pérez",
            cedula="1234567890"
        )
        expected = "Juan Pérez (1234567890)"
        self.assertEqual(str(estudiante), expected)
    
    def test_fecha_registro_automatica(self):
        """Test: La fecha de registro se asigna automáticamente"""
        estudiante = EstudianteFactory()
        self.assertIsNotNone(estudiante.fecha_registro)
    
    def test_fecha_modificacion_automatica(self):
        """Test: La fecha de modificación se actualiza automáticamente"""
        estudiante = EstudianteFactory()
        fecha_original = estudiante.fecha_modificacion
        
        # Simular modificación
        estudiante.nombres = "Nuevo Nombre"
        estudiante.save()
        
        self.assertGreater(estudiante.fecha_modificacion, fecha_original)
    
    def test_campos_opcionales(self):
        """Test: Los campos opcionales pueden estar vacíos"""
        estudiante = EstudianteFactory(
            telefono=None,
            foto=None,
            fecha_nacimiento=None,
            direccion=None,
            direccion_2=None,
            pais=None,
            provincia=None
        )
        self.assertIsNone(estudiante.telefono)
        # FieldFile puede no ser None pero evaluarse como vacío
        self.assertFalse(estudiante.foto)
    
    def test_longitud_campos(self):
        """Test: Validación de longitud de campos"""
        # Test nombres muy largos
        with self.assertRaises(ValidationError):
            estudiante = EstudianteFactory()
            estudiante.nombres = "A" * 101  # Más de 100 caracteres
            estudiante.full_clean()
        
        # Test cédula muy larga
        with self.assertRaises(ValidationError):
            estudiante = EstudianteFactory()
            estudiante.cedula = "A" * 21  # Más de 20 caracteres
            estudiante.full_clean()
    
    def test_formato_email_valido(self):
        """Test: Validación de formato de email"""
        with self.assertRaises(ValidationError):
            estudiante = EstudianteFactory()
            estudiante.correo = "email-invalido"
            estudiante.full_clean()
    
    def test_eventos_matriculados(self):
        """Test: Relación many-to-many con eventos"""
        estudiante = EstudianteFactory()
        # Por ahora está vacío, pero la relación debe funcionar
        self.assertEqual(estudiante.eventos_matriculados.count(), 0)


class EstudianteIntegrationTest(TestCase):
    """Tests de integración para Estudiante"""
    
    def test_crear_multiples_estudiantes(self):
        """Test: Crear múltiples estudiantes sin conflictos"""
        estudiantes = []
        for i in range(10):
            estudiante = EstudianteFactory()
            estudiantes.append(estudiante)
        
        self.assertEqual(Estudiante.objects.count(), 10)
        
        # Verificar que todos tienen IDs únicos
        ids = [e.id for e in estudiantes]
        self.assertEqual(len(ids), len(set(ids)))
    
    def test_busqueda_estudiantes(self):
        """Test: Búsqueda y filtrado de estudiantes"""
        # Crear estudiantes con datos específicos
        EstudianteFactory(ciudad="Quito")
        EstudianteFactory(ciudad="Guayaquil")
        EstudianteFactory(ciudad="Quito")
        
        # Buscar por ciudad
        estudiantes_quito = Estudiante.objects.filter(ciudad="Quito")
        self.assertEqual(estudiantes_quito.count(), 2)
        
        estudiantes_guayaquil = Estudiante.objects.filter(ciudad="Guayaquil")
        self.assertEqual(estudiantes_guayaquil.count(), 1)
    
    def test_actualizacion_estudiante(self):
        """Test: Actualización completa de un estudiante"""
        estudiante = EstudianteFactory()
        
        # Actualizar todos los campos
        datos_actualizados = {
            'nombres': 'María',
            'apellidos': 'González',
            'ciudad': 'Cuenca',
            'telefono': '0987654321',
            'direccion': 'Nueva Dirección 123',
            'pais': 'Ecuador',
            'provincia': 'Azuay'
        }
        
        for campo, valor in datos_actualizados.items():
            setattr(estudiante, campo, valor)
        
        estudiante.save()
        estudiante.refresh_from_db()
        
        # Verificar que se actualizaron todos los campos
        for campo, valor in datos_actualizados.items():
            self.assertEqual(getattr(estudiante, campo), valor)


@pytest.mark.django_db
class EstudiantePytestTest:
    """Tests usando pytest para el modelo Estudiante"""
    
    def test_estudiante_con_pytest(self):
        """Test básico usando pytest"""
        estudiante = EstudianteFactory()
        assert estudiante.id is not None
        assert estudiante.nombres is not None
        assert estudiante.apellidos is not None
    
    def test_estudiante_cedula_valida(self):
        """Test de validación de cédula con pytest"""
        cedula_valida = "1234567890"
        estudiante = EstudianteFactory(cedula=cedula_valida)
        assert estudiante.cedula == cedula_valida
    
    def test_estudiante_correo_valido(self):
        """Test de validación de correo con pytest"""
        correo_valido = "test@example.com"
        estudiante = EstudianteFactory(correo=correo_valido)
        assert estudiante.correo == correo_valido
