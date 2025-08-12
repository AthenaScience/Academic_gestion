from django.contrib import admin
from .models import Evento, Certificado

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'fecha_inicio', 'fecha_fin', 'lugar')
    list_filter = ('tipo',)
    search_fields = ('nombre',)

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'evento', 'generado_en', 'uuid')
    list_filter = ('evento__tipo',)
    search_fields = ('uuid', 'estudiante__nombres', 'estudiante__apellidos')
    fields = ('estudiante', 'evento', 'foto', 'qr','codigo_certificado')

































