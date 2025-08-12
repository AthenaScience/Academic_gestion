#!/usr/bin/env python3
"""
Script para crear el evento DIP-ADM-2024 para pruebas
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_academica.settings')
django.setup()

from modulos.modulo_certificados.models import Evento
from django.utils import timezone
from datetime import timedelta

def crear_evento():
    """Crear el evento DIP-ADM-2024 para pruebas"""
    
    # Verificar si ya existe
    try:
        evento_existente = Evento.objects.get(codigo_evento='DIP-ADM-2024')
        print(f"✅ El evento {evento_existente.nombre} ya existe con ID: {evento_existente.id}")
        return evento_existente
    except Evento.DoesNotExist:
        pass
    
    # Crear el evento
    try:
        evento = Evento.objects.create(
            nombre="Diploma en Administración 2024",
            tipo="diploma",
            codigo_evento="DIP-ADM-2024",
            fecha_inicio=timezone.now().date(),
            fecha_fin=(timezone.now().date() + timedelta(days=180)),
            lugar="Modalidad Virtual",
            aval="UTEQ",
            horas_academicas=120,
            costo_matricula=50.00,
            costo_colegiatura=400.00,
            costo_certificado=25.00,
            requiere_matricula=True,
            permite_pago_certificado_anticipado=True
        )
        
        print(f"✅ Evento creado exitosamente:")
        print(f"   📚 Nombre: {evento.nombre}")
        print(f"   🔢 Código: {evento.codigo_evento}")
        print(f"   🏷️  Tipo: {evento.tipo}")
        print(f"   📍 Lugar: {evento.lugar}")
        print(f"   🏛️  Aval: {evento.aval}")
        print(f"   ⏰ Horas: {evento.horas_academicas}")
        print(f"   💰 Matrícula: ${evento.costo_matricula}")
        print(f"   💰 Colegiatura: ${evento.costo_colegiatura}")
        print(f"   💰 Certificado: ${evento.costo_certificado}")
        print(f"   📅 Fecha inicio: {evento.fecha_inicio}")
        print(f"   📅 Fecha fin: {evento.fecha_fin}")
        # print(f"   💳 Cuotas máximas: {evento.numero_maximo_cuotas}")
        print(f"   💰 Costo total: ${evento.costo_total}")
        
        return evento
        
    except Exception as e:
        print(f"❌ Error al crear el evento: {str(e)}")
        return None

if __name__ == "__main__":
    print("🚀 Creando evento DIP-ADM-2024 para pruebas...")
    evento = crear_evento()
    
    if evento:
        print(f"\n🎉 Evento creado con ID: {evento.id}")
        print("Ahora puedes ejecutar la matriculación masiva.")
    else:
        print("\n❌ No se pudo crear el evento.")
        sys.exit(1)
