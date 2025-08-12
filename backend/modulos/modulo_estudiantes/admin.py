from django.contrib import admin
from .models import Estudiante

@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    @admin.display(description="Eventos Matriculados")
    def lista_eventos(self, obj):
        return ", ".join([e.nombre for e in obj.eventos_matriculados.all()])
    
    list_display = (
        'nombres', 'apellidos', 'cedula', 'correo', 'fecha_registro', 
        'ciudad', 'telefono', 'foto', 
        'fecha_nacimiento', 'direccion', 'direccion_2', 
        'pais', 'provincia', 'codigo_estudiante', 'lista_eventos'
    )
    list_filter = ('cedula',)  # Puedes agregar más campos reales aquí
    search_fields = ('nombres', 'apellidos', 'cedula', 'correo','codigo_estudiante','lista_eventos')
