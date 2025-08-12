from django.contrib import admin
from django import forms
from django.db import models
from decimal import Decimal
from .models import (
    PlanPago,
    Cuota, 
    Pago, 
    PagoCuota,
    PagoCuotaAplicada,
    InstitucionFinanciera,
    EstadoPagosEvento, 
    Matricula,
    Beca,
    Descuento,
    CostoMiscelaneo,
)
from .services.sistema_pagos_service import SistemaPagosService
from modulos.modulo_certificados.models import Evento

# Register your models here.

@admin.register(InstitucionFinanciera)
class InstitucionFinancieraAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo_institucion', 'activo', 'fecha_creacion']
    list_filter = ['tipo_institucion', 'activo']
    search_fields = ['codigo', 'nombre']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    ordering = ['nombre']

@admin.register(Beca)
class BecaAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_beca', 'estudiante', 'evento', 'tipo_beca', 
        'estado', 'fecha_inicio', 'fecha_fin', 'esta_activa'
    ]
    list_filter = [
        'tipo_beca', 'estado', 'aplica_matricula', 
        'aplica_colegiatura', 'aplica_certificado',
        'fecha_inicio', 'fecha_fin'
    ]
    search_fields = [
        'nombre_beca', 'estudiante__nombres', 'estudiante__apellidos',
        'estudiante__cedula', 'evento__nombre', 'motivo', 'aprobado_por'
    ]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'fecha_aprobacion']
    fieldsets = (
        ('Información Básica', {
            'fields': ('estudiante', 'evento', 'nombre_beca', 'tipo_beca')
        }),
        ('Descuento', {
            'fields': ('porcentaje_descuento', 'monto_descuento')
        }),
        ('Aplicación', {
            'fields': ('aplica_matricula', 'aplica_colegiatura', 'aplica_certificado')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio', 'fecha_fin', 'estado')
        }),
        ('Información Adicional', {
            'fields': ('motivo', 'documentos_soporte', 'aprobado_por')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion', 'fecha_aprobacion'),
            'classes': ('collapse',)
        })
    )
    
    def esta_activa(self, obj):
        return obj.esta_activa
    esta_activa.boolean = True
    esta_activa.short_description = '¿Está Activa?'

@admin.register(Descuento)
class DescuentoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_descuento', 'estudiante', 'evento', 'tipo_descuento',
        'estado', 'fecha_inicio', 'fecha_fin', 'esta_activo', 'codigo_promocional'
    ]
    list_filter = [
        'tipo_descuento', 'estado', 'aplica_matricula',
        'aplica_colegiatura', 'aplica_certificado',
        'fecha_inicio', 'fecha_fin'
    ]
    search_fields = [
        'nombre_descuento', 'estudiante__nombres', 'estudiante__apellidos',
        'estudiante__cedula', 'evento__nombre', 'motivo', 'codigo_promocional'
    ]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    fieldsets = (
        ('Información Básica', {
            'fields': ('estudiante', 'evento', 'nombre_descuento', 'tipo_descuento')
        }),
        ('Descuento', {
            'fields': ('porcentaje_descuento', 'monto_descuento')
        }),
        ('Aplicación', {
            'fields': ('aplica_matricula', 'aplica_colegiatura', 'aplica_certificado')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio', 'fecha_fin', 'estado')
        }),
        ('Información Adicional', {
            'fields': ('motivo', 'codigo_promocional')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        })
    )
    
    def esta_activo(self, obj):
        return obj.esta_activo
    esta_activo.boolean = True
    esta_activo.short_description = '¿Está Activo?'

# Eliminado: PlanPagoPersonalizado (modelo deprecado) – sección removida

@admin.register(PlanPago)
class PlanPagoAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'evento', 'monto_colegiatura', 'numero_cuotas', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'evento']
    search_fields = ['estudiante__nombres', 'estudiante__apellidos', 'estudiante__cedula', 'evento__nombre']

    # Ocultar del índice del admin (se usa solo para autocompletar)
    def get_model_perms(self, request):
        return {}


class CuotaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"Cuota {obj.numero_cuota} - ${obj.monto}"


class PagoAdminForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Extraer datos del formulario
        estudiante_id = None
        evento_id = None
        tipo_pago = None
        
        # Obtener datos de diferentes fuentes
        if self.data:
            estudiante_id = self.data.get('estudiante')
            evento_id = self.data.get('evento')
            tipo_pago = self.data.get('tipo_pago')
        elif self.instance and self.instance.pk:
            estudiante_id = self.instance.estudiante_id
            evento_id = self.instance.evento_id
            tipo_pago = self.instance.tipo_pago
        
        # Convertir a enteros si es necesario
        try:
            estudiante_id = int(estudiante_id) if estudiante_id else None
            evento_id = int(evento_id) if evento_id else None
        except (ValueError, TypeError):
            estudiante_id = None
            evento_id = None
        
        # Configurar campo evento
        if 'evento' in self.fields:
            self.fields['evento'].queryset = Evento.objects.all()
            self.fields['evento'].help_text = (
                "Seleccione un evento. La validación verificará que el estudiante esté matriculado."
            )
        
        # Configurar campo cuota dinámicamente
        if 'cuota' in self.fields:
            cuotas_queryset = Cuota.objects.none()
            help_text = "Para ver cuotas: 1) Seleccione estudiante, 2) Seleccione evento, 3) Seleccione 'Cuota Individual', 4) Guarde para ver cuotas disponibles."
            
            # Si tenemos todos los datos necesarios para cuota individual
            if estudiante_id and evento_id and tipo_pago == 'cuota_individual':
                try:
                    from modulos.modulo_estudiantes.models import Estudiante
                    estudiante = Estudiante.objects.get(id=estudiante_id)
                    evento = Evento.objects.get(id=evento_id)
                    
                    # Verificar que esté matriculado
                    if estudiante.eventos_matriculados.filter(id=evento_id).exists():
                        # Buscar plan actual
                        plan_estandar = PlanPago.objects.filter(
                            estudiante=estudiante, evento=evento
                        ).first()
                        
                        if plan_estandar:
                            # Verificar si el plan está desactualizado (costo del evento cambió)
                            plan_desactualizado = plan_estandar.monto_colegiatura != evento.costo_colegiatura
                            
                            if plan_desactualizado:
                                try:
                                    # Actualizar plan y regenerar cuotas
                                    plan_estandar.monto_colegiatura = evento.costo_colegiatura
                                    plan_estandar.save()
                                    
                                    # Eliminar cuotas pendientes existentes
                                    plan_estandar.cuotas.filter(estado='pendiente').delete()
                                    
                                    # Regenerar cuotas con nuevo precio
                                    from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService
                                    SistemaPagosService.generar_cuotas_plan(plan_estandar)
                                    
                                    # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                                    cuotas_queryset = Cuota.objects.filter(
                                        plan_pago=plan_estandar
                                    ).exclude(
                                        monto_pagado__gte=models.F('monto')
                                    ).order_by('numero_cuota')
                                    help_text = f"✅ {cuotas_queryset.count()} cuotas actualizadas (Plan Estándar - precio actualizado)"
                                except Exception as e:
                                    help_text = f"❌ Error actualizando plan: {str(e)[:50]}..."
                                    cuotas_queryset = Cuota.objects.none()
                            else:
                                # Plan está actualizado, usar cuotas existentes
                                # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                                cuotas_queryset = Cuota.objects.filter(
                                    plan_pago=plan_estandar
                                ).exclude(
                                    monto_pagado__gte=models.F('monto')
                                ).order_by('numero_cuota')
                                
                                if cuotas_queryset.exists():
                                    help_text = f"✅ {cuotas_queryset.count()} cuotas pendientes (Plan Estándar)"
                                else:
                                    # Regenerar cuotas si no existen
                                    try:
                                        from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService
                                        SistemaPagosService.generar_cuotas_plan(plan_estandar)
                                        # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                                        cuotas_queryset = Cuota.objects.filter(
                                            plan_pago=plan_estandar
                                        ).exclude(
                                            monto_pagado__gte=models.F('monto')
                                        ).order_by('numero_cuota')
                                        help_text = f"✅ {cuotas_queryset.count()} cuotas regeneradas (Plan Estándar)"
                                    except Exception as e:
                                        help_text = f"❌ Error regenerando cuotas: {str(e)[:50]}..."
                        else:
                                # No hay ningún plan - crear plan estándar automáticamente
                                try:
                                    # Verificar si ya existe EstadoPagosEvento
                                    estado = EstadoPagosEvento.objects.filter(
                                        estudiante=estudiante, evento=evento
                                    ).first()
                                    
                                    if estado:
                                        # Crear solo el plan y cuotas (EstadoPagosEvento ya existe)
                                        plan_estandar = PlanPago.objects.create(
                                            estudiante=estudiante,
                                            evento=evento,
                                            monto_colegiatura=evento.costo_colegiatura,
                                            numero_cuotas=1
                                        )
                                        
                                        # Generar cuotas
                                        from modulos.modulo_pagos.services.sistema_pagos_service import SistemaPagosService
                                        SistemaPagosService.generar_cuotas_plan(plan_estandar)
                                        
                                        # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                                        cuotas_queryset = Cuota.objects.filter(
                                            plan_pago=plan_estandar
                                        ).exclude(
                                            monto_pagado__gte=models.F('monto')
                                        ).order_by('numero_cuota')
                                        help_text = f"✅ Plan creado automáticamente - {cuotas_queryset.count()} cuotas pendientes"
                                    else:
                                        # Crear plan completo (incluye EstadoPagosEvento)
                                        SistemaPagosService.crear_plan_pago_estudiante(
                                            estudiante, evento
                                         )
                                        plan_estandar = PlanPago.objects.filter(
                                            estudiante=estudiante, evento=evento
                                        ).first()
                                        
                                        if plan_estandar:
                                            # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                                            cuotas_queryset = Cuota.objects.filter(
                                                plan_pago=plan_estandar
                                            ).exclude(
                                                monto_pagado__gte=models.F('monto')
                                            ).order_by('numero_cuota')
                                            help_text = f"✅ Plan completo creado automáticamente - {cuotas_queryset.count()} cuotas pendientes"
                                        else:
                                            help_text = "❌ Error al crear plan automático"
                                except Exception as e:
                                    help_text = f"❌ Error creando plan: {str(e)[:100]}..."
                                    cuotas_queryset = Cuota.objects.none()
                    else:
                        help_text = "❌ El estudiante no está matriculado en este evento"
                        
                except (Estudiante.DoesNotExist, Evento.DoesNotExist, ValueError):
                    help_text = "❌ Error: Estudiante o evento no válido"
            
            elif self.instance and self.instance.pk and self.instance.cuota:
                # Editando pago existente
                cuotas_queryset = Cuota.objects.filter(id=self.instance.cuota.id)
                help_text = "Cuota actual del pago"
            
            self.fields['cuota'] = CuotaChoiceField(
                queryset=cuotas_queryset,
                required=False
            )
            self.fields['cuota'].help_text = help_text

        # Campo adicional: selección múltiple de cuotas para pagos de colegiatura parcial/total
        # Se muestra solo si hay contexto suficiente
        try:
            if estudiante_id and evento_id and tipo_pago in ['colegiatura_parcial', 'colegiatura_total']:
                from modulos.modulo_pagos.models import PlanPago as PlanPagoModel, Cuota as CuotaModel
                plan_actual = PlanPagoModel.objects.filter(
                    estudiante_id=estudiante_id, evento_id=evento_id
                ).first()
                cuotas_qs = CuotaModel.objects.none()
                if plan_actual:
                    # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                    cuotas_qs = CuotaModel.objects.filter(
                        plan_pago=plan_actual
                    ).exclude(
                        monto_pagado__gte=models.F('monto')
                    ).order_by('numero_cuota')

                self.fields['cuotas_ids'] = forms.ModelMultipleChoiceField(
                    queryset=cuotas_qs,
                    required=False,
                    help_text=(
                        "Seleccione cuotas a las que aplicar el pago. "
                        "Si no selecciona, se aplicará automáticamente en orden a las pendientes."
                    )
                )
        except Exception:
            # No bloquear el formulario por errores de contexto
            pass
        
        # Personalizar ayuda para campos según tipo de pago
        if 'monto' in self.fields:
            self.fields['monto'].help_text = (
                "Monto del pago. Para cuota individual: máximo el pendiente de la cuota. "
                "Para pago parcial: se distribuirá entre cuotas pendientes. "
                "Para pago total: debe cubrir todas las cuotas pendientes."
            )
            
        if 'observaciones' in self.fields:
            self.fields['observaciones'].help_text = (
                "Observaciones adicionales. Obligatorio para pagos misceláneos."
            )
        
        # Hacer el campo monto_aplicado_colegiatura opcional
        if 'monto_aplicado_colegiatura' in self.fields:
            self.fields['monto_aplicado_colegiatura'].required = False
            self.fields['monto_aplicado_colegiatura'].help_text = (
                "Opcional. Si no se especifica, se usará el valor del campo 'Monto'."
            )
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_pago = cleaned_data.get('tipo_pago')
        estudiante = cleaned_data.get('estudiante')
        evento = cleaned_data.get('evento')
        cuota = cleaned_data.get('cuota')
        monto = cleaned_data.get('monto')
        
        # Validar que pagos misceláneos tengan observaciones
        if tipo_pago == 'miscelaneo':
            observaciones = cleaned_data.get('observaciones')
            if not observaciones or not observaciones.strip():
                raise forms.ValidationError({
                    'observaciones': 'Las observaciones son obligatorias para pagos misceláneos.'
                })
        
        # Para pagos misceláneos, evento es opcional
        if tipo_pago == 'miscelaneo':
            return cleaned_data
        
        # Para otros tipos de pago, validar estudiante y evento
        if not estudiante:
            raise forms.ValidationError({
                'estudiante': 'Debe seleccionar un estudiante.'
            })
            
        if not evento and tipo_pago in ['cuota_individual', 'colegiatura_parcial', 'colegiatura_total', 'matricula', 'certificado']:
            raise forms.ValidationError({
                'evento': 'Debe seleccionar un evento para este tipo de pago.'
            })
        
        # Validar que el estudiante esté matriculado en el evento para pagos relacionados
        if estudiante and evento and tipo_pago in ['cuota_individual', 'colegiatura_parcial', 'colegiatura_total', 'matricula', 'certificado']:
            if not estudiante.eventos_matriculados.filter(id=evento.id).exists():
                eventos_disponibles = list(estudiante.eventos_matriculados.values_list('nombre', flat=True))
                if eventos_disponibles:
                    eventos_texto = ', '.join(eventos_disponibles)
                    mensaje = f'El estudiante {estudiante} no está matriculado en "{evento}". Eventos disponibles: {eventos_texto}'
                else:
                    mensaje = f'El estudiante {estudiante} no está matriculado en ningún evento. Debe matricularlo primero.'
                    
                raise forms.ValidationError({
                    'evento': mensaje
                })
        
        # Validaciones específicas por tipo de pago
        if tipo_pago == 'cuota_individual':
            if not cuota:
                # Buscar cuotas disponibles en cualquier tipo de plan
                cuotas_estandar = 0
                cuotas_personalizado = 0
                
                # Buscar plan actual unificado
                plan_estandar = PlanPago.objects.filter(
                    estudiante=estudiante, evento=evento
                ).first()
                if plan_estandar:
                    # Contar cuotas con saldo pendiente (no solo estado pendiente)
                    cuotas_estandar = Cuota.objects.filter(
                        plan_pago=plan_estandar
                    ).exclude(
                        monto_pagado__gte=models.F('monto')
                    ).count()
                
                # Planes personalizados deprecados (no considerar)
                cuotas_personalizado = 0
                
                total_cuotas = cuotas_estandar + cuotas_personalizado
                
                if total_cuotas > 0:
                    tipo_plan = "estándar" if cuotas_estandar > 0 else "personalizado"
                    raise forms.ValidationError({
                        'cuota': f'Debe seleccionar una cuota. Hay {total_cuotas} cuotas pendientes ({tipo_plan}). Recargue la página después de seleccionar estudiante, evento y tipo de pago.'
                    })
                else:
                    raise forms.ValidationError({
                        'cuota': 'No hay cuotas pendientes para este estudiante en este evento.'
                    })
            
            if cuota and estudiante and evento:
                # Validar que la cuota pertenezca al estudiante/evento (estándar o personalizado)
                cuota_valida = False
                
                if hasattr(cuota, 'plan_pago') and cuota.plan_pago:
                    cuota_valida = (cuota.plan_pago.estudiante == estudiante and
                                   cuota.plan_pago.evento == evento)
                
                if not cuota_valida:
                    raise forms.ValidationError({
                        'cuota': 'La cuota seleccionada no corresponde al estudiante y evento seleccionados.'
                    })
                    
                # Validar que no se pague más de lo que falta
                monto_pendiente = cuota.monto - (cuota.monto_pagado or Decimal('0.00'))
                if monto and monto > monto_pendiente:
                    raise forms.ValidationError({
                        'monto': f'El monto no puede ser mayor al pendiente de la cuota (${monto_pendiente}).'
                    })
        
        elif tipo_pago in ['colegiatura_parcial', 'colegiatura_total']:
            if not evento:
                raise forms.ValidationError({
                    'evento': 'Debe seleccionar un evento para pagos de colegiatura.'
                })
                
            # Validar que hay cuotas pendientes
            if estudiante and evento:
                plan = PlanPago.objects.filter(
                    estudiante=estudiante, evento=evento
                ).first()
                
                if plan:
                    # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                    cuotas_pendientes = Cuota.objects.filter(
                        plan_pago=plan
                    ).exclude(
                        monto_pagado__gte=models.F('monto')
                    )
                    
                    if not cuotas_pendientes.exists():
                        raise forms.ValidationError({
                            'tipo_pago': 'No hay cuotas pendientes para este estudiante en este evento.'
                        })
                        
                    # Para pago total, validar que el monto cubra todas las cuotas pendientes
                    if tipo_pago == 'colegiatura_total':
                        total_pendiente = sum(c.monto - (c.monto_pagado or Decimal('0.00')) for c in cuotas_pendientes)
                        if monto and monto < total_pendiente:
                            raise forms.ValidationError({
                                'monto': f'Para pago total, el monto debe ser al menos ${total_pendiente} (total pendiente).'
                            })
        
        return cleaned_data


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    form = PagoAdminForm
    list_display = ['estudiante', 'evento', 'tipo_pago', 'monto', 'metodo_pago', 'fecha_pago']
    list_filter = ['tipo_pago', 'metodo_pago', 'fecha_pago']
    search_fields = [
        'estudiante__nombres', 'estudiante__apellidos', 'estudiante__cedula',
        'evento__nombre', 'numero_transaccion'
    ]
    autocomplete_fields = ['estudiante', 'costo_miscelaneo']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Personalizar campos según el contexto
        if obj and obj.estudiante:
            # Si estamos editando un pago existente, filtrar por el estudiante
            eventos_matriculados = obj.estudiante.eventos_matriculados.all()
            form.base_fields['evento'].queryset = eventos_matriculados
            
            if obj.evento and obj.tipo_pago == 'cuota_individual':
                # Cargar cuotas pendientes para este estudiante y evento
                plan = PlanPago.objects.filter(
                    estudiante=obj.estudiante, evento=obj.evento
                ).first()
                if plan:
                    # Filtrar cuotas con saldo pendiente (no solo estado pendiente)
                    cuotas_pendientes = Cuota.objects.filter(
                        plan_pago=plan
                    ).exclude(
                        monto_pagado__gte=models.F('monto')
                    ).order_by('numero_cuota')
                    form.base_fields['cuota'] = CuotaChoiceField(
                        queryset=cuotas_pendientes, required=False
                    )
        else:
            # Para pagos nuevos, mostrar todos los eventos inicialmente
            # El filtrado se hará vía validación en el formulario
            form.base_fields['evento'].queryset = Evento.objects.all()
            form.base_fields['cuota'] = CuotaChoiceField(
                queryset=Cuota.objects.none(), required=False
            )
        
        return form

    def save_model(self, request, obj, form, change):
        # Permitir aplicar pagos de colegiatura a cuotas seleccionadas desde el admin
        cuotas = form.cleaned_data.get('cuotas_ids') if hasattr(form, 'cleaned_data') else None
        if cuotas:
            try:
                obj._cuotas_ids_prefijadas = list(cuotas.values_list('id', flat=True))
            except Exception:
                obj._cuotas_ids_prefijadas = [c.id for c in cuotas]
        super().save_model(request, obj, form, change)


@admin.register(CostoMiscelaneo)
class CostoMiscelaneoAdmin(admin.ModelAdmin):
    list_display = ['evento', 'descripcion', 'monto', 'es_obligatorio', 'fecha_creacion']
    list_filter = ['evento', 'es_obligatorio']
    search_fields = ['evento__nombre', 'descripcion']


@admin.register(Cuota)
class CuotaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_cuota', 'plan_pago', 'estudiante', 'evento', 'monto', 
        'fecha_vencimiento', 'estado', 'fecha_pago', 'monto_pagado'
    ]
    list_filter = ['estado', 'fecha_vencimiento', 'fecha_pago']
    search_fields = [
        'plan_pago__estudiante__nombres',
        'plan_pago__estudiante__apellidos',
        'plan_pago__evento__nombre',
    ]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    autocomplete_fields = ['plan_pago']

    # Ocultar del índice del admin (se usa solo para autocompletar)
    def get_model_perms(self, request):
        return {}
    fieldsets = (
        ('Información de la Cuota', {
            'fields': ('numero_cuota', 'monto', 'fecha_vencimiento', 'estado')
        }),
        ('Plan de Pago', {
            'fields': ('plan_pago',)
        }),
        ('Pago', {
            'fields': ('fecha_pago', 'monto_pagado', 'observaciones')
        }),
        ('Comprobante', {
            'fields': ('comprobante', 'institucion_financiera', 'codigo_comprobante')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        })
    )
    
    def estudiante(self, obj):
        return obj.estudiante
    estudiante.short_description = 'Estudiante'
    
    def evento(self, obj):
        return obj.evento
    evento.short_description = 'Evento'
    
    def plan_pago(self, obj):
        return obj.plan_pago
    plan_pago.short_description = 'Plan de Pago'

@admin.register(PagoCuotaAplicada)
class PagoCuotaAplicadaAdmin(admin.ModelAdmin):
    list_display = ['pago', 'cuota', 'estudiante', 'evento', 'monto_aplicado', 'fecha_aplicacion']
    list_filter = ['fecha_aplicacion']
    search_fields = [
        'pago__estudiante__nombres', 'pago__estudiante__apellidos',
        'cuota__plan_pago__evento__nombre'
    ]
    readonly_fields = ['fecha_aplicacion']
    
    def estudiante(self, obj):
        return obj.pago.estudiante
    estudiante.short_description = 'Estudiante'
    
    def evento(self, obj):
        return obj.cuota.plan_pago.evento if obj.cuota.plan_pago else 'N/A'
    evento.short_description = 'Evento'
    
    # Ocultar del índice del admin
    def get_model_perms(self, request):
        return {}


@admin.register(PagoCuota)
class PagoCuotaAdmin(admin.ModelAdmin):
    list_display = [
        'cuota', 'estudiante', 'evento', 'monto_pagado', 'fecha_pago', 
        'metodo_pago', 'institucion_financiera', 'codigo_comprobante'
    ]
    list_filter = ['metodo_pago', 'fecha_pago', 'institucion_financiera']
    search_fields = [
        'cuota__plan_pago__estudiante__nombres',
        'cuota__plan_pago__estudiante__apellidos',
        'codigo_comprobante', 'numero_transaccion'
    ]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    fieldsets = (
        ('Información del Pago', {
            'fields': ('cuota', 'monto_pagado', 'fecha_pago', 'metodo_pago')
        }),
        ('Comprobante', {
            'fields': ('institucion_financiera', 'codigo_comprobante', 'comprobante')
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'numero_transaccion')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        })
    )
    
    def estudiante(self, obj):
        return obj.estudiante
    estudiante.short_description = 'Estudiante'
    
    def evento(self, obj):
        return obj.evento
    evento.short_description = 'Evento'

    # Ocultar del índice del admin (se usa solo para autocompletar)
    def get_model_perms(self, request):
        return {}


# ==================== ADMINISTRACIÓN DE MATRÍCULA ====================

class MatriculaAdminForm(forms.ModelForm):
    """Form personalizado para matrícula con campos de plan de pago anidados"""
    
    # Campos del plan de pago
    numero_cuotas = forms.IntegerField(
        min_value=1, max_value=60, required=True,
        help_text="Número de cuotas en que se diferirá la colegiatura"
    )
    monto_colegiatura = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        help_text="Monto de colegiatura (opcional si no es personalizado)"
    )
    usa_monto_personalizado = forms.BooleanField(
        required=False, initial=False,
        help_text="Si no se marca, se usará el costo de colegiatura del evento"
    )
    aplicar_beca_descuentos = forms.BooleanField(
        required=False, initial=True,
        help_text="Aplicar automáticamente becas y descuentos seleccionados"
    )
    becas = forms.ModelMultipleChoiceField(
        queryset=Beca.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    descuentos = forms.ModelMultipleChoiceField(
        queryset=Descuento.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    tiene_convenio = forms.BooleanField(
        required=False, initial=False,
        help_text="Indica si tiene un convenio de pago especial"
    )
    constancia_convenio = forms.FileField(
        required=False,
        help_text="Documento de constancia del convenio de pago"
    )
    motivo_convenio = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), required=False,
        help_text="Motivo del convenio de pago"
    )
    
    class Meta:
        model = Matricula
        fields = [
            'estudiante', 'evento', 'estado', 'comprobante_matricula', 'observaciones',
            # Campos del plan de pago
            'numero_cuotas', 'monto_colegiatura', 'usa_monto_personalizado', 
            'aplicar_beca_descuentos', 'becas', 'descuentos',
            'tiene_convenio', 'constancia_convenio', 'motivo_convenio'
        ]

    def __init__(self, *args, **kwargs):
        # Cargar datos del plan de pago existente ANTES de llamar super() 
        # para que los valores iniciales se configuren correctamente
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {})
        
        if instance and instance.pk and instance.plan_pago:
            plan = instance.plan_pago
            initial.update({
                'numero_cuotas': plan.numero_cuotas,
                'monto_colegiatura': plan.monto_colegiatura,
                'usa_monto_personalizado': plan.usa_monto_personalizado,
                'aplicar_beca_descuentos': plan.aplicar_beca_descuentos,
                'becas': plan.becas.all(),
                'descuentos': plan.descuentos.all(),
                'tiene_convenio': plan.tiene_convenio,
                'motivo_convenio': plan.motivo_convenio,
            })
            kwargs['initial'] = initial
        else:
            # Para nueva matrícula, establecer valores por defecto
            initial.update({
                'numero_cuotas': 12,
                'usa_monto_personalizado': False,
                'aplicar_beca_descuentos': True,
                'tiene_convenio': False,
            })
            kwargs['initial'] = initial
        
        super().__init__(*args, **kwargs)
        
        # Configurar filtros dinámicos después de super()
        if 'estudiante' in self.data:
            try:
                estudiante_id = int(self.data.get('estudiante'))
                # Filtrar eventos disponibles para el estudiante
                from modulos.modulo_estudiantes.models import Estudiante
                estudiante = Estudiante.objects.get(id=estudiante_id)
                
                if self.instance.pk:
                    # Para matrícula existente: mostrar solo eventos matriculados
                    self.fields['evento'].queryset = estudiante.eventos_matriculados.all()
                else:
                    # Para nueva matrícula: mostrar todos los eventos disponibles
                    # (pueden matricularse en eventos que no tengan aún)
                    self.fields['evento'].queryset = Evento.objects.all()
                
                # Filtrar becas y descuentos por estudiante
                self.fields['becas'].queryset = Beca.objects.filter(
                    estudiante=estudiante, estado='activa'
                )
                self.fields['descuentos'].queryset = Descuento.objects.filter(
                    estudiante=estudiante, estado='activo'
                )
            except (ValueError, TypeError, Estudiante.DoesNotExist):
                self.fields['evento'].queryset = Evento.objects.all() if not self.instance.pk else Evento.objects.none()
                self.fields['becas'].queryset = Beca.objects.none()
                self.fields['descuentos'].queryset = Descuento.objects.none()
        elif self.instance.pk and self.instance.estudiante:
            # Matrícula existente: solo eventos matriculados
            self.fields['evento'].queryset = self.instance.estudiante.eventos_matriculados.all()
            # Filtrar becas y descuentos por estudiante y evento
            self.fields['becas'].queryset = Beca.objects.filter(
                estudiante=self.instance.estudiante, 
                evento=self.instance.evento, 
                estado='activa'
            )
            self.fields['descuentos'].queryset = Descuento.objects.filter(
                estudiante=self.instance.estudiante, 
                evento=self.instance.evento, 
                estado='activo'
            )
        else:
            # Formulario nuevo sin estudiante seleccionado: mostrar todos los eventos
            self.fields['evento'].queryset = Evento.objects.all()
            self.fields['becas'].queryset = Beca.objects.none()
            self.fields['descuentos'].queryset = Descuento.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        estudiante = cleaned_data.get('estudiante')
        evento = cleaned_data.get('evento')
        usa_monto_personalizado = cleaned_data.get('usa_monto_personalizado')
        monto_colegiatura = cleaned_data.get('monto_colegiatura')
        numero_cuotas = cleaned_data.get('numero_cuotas')
        
        # Debug temporal - Remover en producción
        # print(f"DEBUG - Form clean: numero_cuotas={numero_cuotas}, data_numero_cuotas={self.data.get('numero_cuotas')}")
        # print(f"DEBUG - All cleaned_data keys: {list(cleaned_data.keys())}")
        
        if estudiante and evento:
            # Verificar que no exista ya una matrícula para este estudiante en este evento
            if not self.instance.pk:  # Solo en creación
                existing_matricula = Matricula.objects.filter(estudiante=estudiante, evento=evento).first()
                if existing_matricula:
                    raise forms.ValidationError(
                        f"Ya existe una matrícula (ID: {existing_matricula.id}) para {estudiante} en {evento}"
                    )
            # Para matrículas existentes, no hay validaciones adicionales necesarias
        
        # Validar monto personalizado
        if usa_monto_personalizado and not monto_colegiatura:
            raise forms.ValidationError(
                "Debe especificar el monto de colegiatura si usa monto personalizado"
            )
        
        return cleaned_data

    def save(self, commit=True):
        # print(f"DEBUG - MatriculaAdminForm.save called with commit={commit}")
        matricula = super().save(commit=False)
        
        # Si es una nueva matrícula, agregar el estudiante al evento ANTES de crear el plan
        is_new_matricula = not self.instance.pk
        if is_new_matricula and matricula.estudiante and matricula.evento:
            # Agregar la relación M2M independientemente de si ya existe
            matricula.estudiante.eventos_matriculados.add(matricula.evento)
        
        # SIEMPRE guardar la matrícula primero
        if commit:
            matricula.save()
            # print(f"DEBUG - Matricula saved: {matricula.id}")
        
        # Procesar plan de pago SIEMPRE (tanto en commit=True como commit=False)
        # porque el admin llama save(commit=False) seguido de save_m2m()
        self._save_plan_pago(matricula)
                
        return matricula
    
    def _save_plan_pago(self, matricula):
        """Método separado para guardar/actualizar el plan de pago"""
        # Solo procesar plan de pago si hay datos válidos en cleaned_data
        numero_cuotas = self.cleaned_data.get('numero_cuotas')
        # print(f"DEBUG - _save_plan_pago: numero_cuotas={numero_cuotas}")
        
        if numero_cuotas is None:
            # print("DEBUG - No numero_cuotas found, skipping plan update")
            return
        
        # Crear o actualizar plan de pago
        plan_data = {
            'numero_cuotas': numero_cuotas,
            'usa_monto_personalizado': self.cleaned_data.get('usa_monto_personalizado', False),
            'aplicar_beca_descuentos': self.cleaned_data.get('aplicar_beca_descuentos', True),
            'tiene_convenio': self.cleaned_data.get('tiene_convenio', False),
            'motivo_convenio': self.cleaned_data.get('motivo_convenio', ''),
        }
        
        # Determinar monto de colegiatura
        if self.cleaned_data.get('usa_monto_personalizado', False):
            plan_data['monto_colegiatura'] = self.cleaned_data.get('monto_colegiatura') or matricula.evento.costo_colegiatura
        else:
            plan_data['monto_colegiatura'] = matricula.evento.costo_colegiatura
        
        # print(f"DEBUG - plan_data: {plan_data}")
        
        if matricula.plan_pago:
            # Actualizar plan existente
            for field, value in plan_data.items():
                # print(f"DEBUG - Setting {field} = {value} on existing plan")
                setattr(matricula.plan_pago, field, value)
            if self.cleaned_data.get('constancia_convenio'):
                matricula.plan_pago.constancia_convenio = self.cleaned_data['constancia_convenio']
            matricula.plan_pago.save()
            plan = matricula.plan_pago
            # print(f"DEBUG - Updated existing plan: {plan.id}, numero_cuotas={plan.numero_cuotas}")
        else:
            # Verificar si ya existe un plan para este estudiante y evento
            existing_plan = PlanPago.objects.filter(
                estudiante=matricula.estudiante,
                evento=matricula.evento
            ).first()
            
            if existing_plan:
                # Usar el plan existente y actualizarlo
                for field, value in plan_data.items():
                    setattr(existing_plan, field, value)
                if self.cleaned_data.get('constancia_convenio'):
                    existing_plan.constancia_convenio = self.cleaned_data['constancia_convenio']
                existing_plan.save()
                plan = existing_plan
                matricula.plan_pago = plan
            else:
                # Crear nuevo plan
                plan = PlanPago.objects.create(
                    estudiante=matricula.estudiante,
                    evento=matricula.evento,
                    constancia_convenio=self.cleaned_data.get('constancia_convenio'),
                    **plan_data
                )
                matricula.plan_pago = plan
            
            # Solo guardar con update_fields si la matrícula ya tiene PK
            if matricula.pk:
                matricula.save(update_fields=['plan_pago'])
            # Si no tiene PK, se guardará cuando el admin haga el save final
        
        # Actualizar becas y descuentos
        plan.becas.set(self.cleaned_data.get('becas', []))
        plan.descuentos.set(self.cleaned_data.get('descuentos', []))
        
        # Generar cuotas
        plan.generar_cuotas()
        # print(f"DEBUG - Generated cuotas for plan {plan.id}")
    
    def save_m2m(self):
        """Django llama este método después de save(commit=False) para guardar relaciones M2M"""
        # print("DEBUG - save_m2m called")
        # Asegurar que el plan se guarde en save_m2m también
        if hasattr(self, 'instance') and self.instance.pk:
            self._save_plan_pago(self.instance)


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    form = MatriculaAdminForm
    
    list_display = [
        'estudiante', 'evento', 'estado', 'fecha_matricula', 
        'tiene_plan_pago', 'numero_cuotas_plan', 'tiene_convenio'
    ]
    list_filter = [
        'estado', 'fecha_matricula', 'evento',
        'plan_pago__tiene_convenio', 'plan_pago__usa_monto_personalizado'
    ]
    search_fields = [
        'estudiante__nombres', 'estudiante__apellidos', 'estudiante__cedula',
        'evento__nombre', 'observaciones'
    ]
    readonly_fields = ['fecha_matricula']
    autocomplete_fields = ['estudiante', 'evento']
    
    fieldsets = (
        ('Información de la Matrícula', {
            'fields': (
                ('estudiante', 'evento'),
                'estado',
                'comprobante_matricula',
                'observaciones'
            )
        }),
        ('Plan de Pago', {
            'fields': (
                ('numero_cuotas', 'usa_monto_personalizado'),
                'monto_colegiatura',
                'aplicar_beca_descuentos',
                'becas',
                'descuentos',
            )
        }),
        ('Convenio de Pago', {
            'fields': (
                'tiene_convenio',
                'constancia_convenio',
                'motivo_convenio',
            ),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_matricula',),
            'classes': ('collapse',)
        })
    )
    
    def tiene_plan_pago(self, obj):
        return bool(obj.plan_pago)
    tiene_plan_pago.boolean = True
    tiene_plan_pago.short_description = 'Plan de Pago'
    
    def numero_cuotas_plan(self, obj):
        return obj.plan_pago.numero_cuotas if obj.plan_pago else '-'
    numero_cuotas_plan.short_description = 'Núm. Cuotas'
    
    def tiene_convenio(self, obj):
        return obj.plan_pago.tiene_convenio if obj.plan_pago else False
    tiene_convenio.boolean = True
    tiene_convenio.short_description = 'Convenio'
    
    actions = ['reestructurar_plan_pago']
    
    def reestructurar_plan_pago(self, request, queryset):
        """Acción para reestructurar plan de pago individual"""
        if queryset.count() != 1:
            self.message_user(
                request, 
                "Seleccione exactamente una matrícula para reestructurar su plan de pago.",
                level='ERROR'
            )
            return
        
        matricula = queryset.first()
        if not matricula.plan_pago:
            self.message_user(
                request, 
                f"La matrícula de {matricula.estudiante} no tiene plan de pago asociado.",
                level='ERROR'
            )
            return
        
        # Redireccionar a una vista personalizada de reestructuración
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(
            reverse('admin:reestructurar_plan_pago', kwargs={'matricula_id': matricula.id})
        )
    
    reestructurar_plan_pago.short_description = "Reestructurar plan de pago seleccionado"

    def get_urls(self):
        """Agregar URLs personalizadas para reestructuración"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'reestructurar/<int:matricula_id>/',
                self.admin_site.admin_view(self.reestructurar_plan_view),
                name='reestructurar_plan_pago',
            ),
        ]
        return custom_urls + urls

    def reestructurar_plan_view(self, request, matricula_id):
        """Vista personalizada para reestructurar plan de pago"""
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages
        from django import forms
        
        matricula = get_object_or_404(Matricula, id=matricula_id)
        if not matricula.plan_pago:
            messages.error(request, "La matrícula no tiene plan de pago asociado.")
            return redirect('admin:modulo_pagos_matricula_changelist')
        
        class ReestructurarPlanForm(forms.Form):
            nuevo_numero_cuotas = forms.IntegerField(
                label="Nuevo número de cuotas",
                min_value=1, max_value=60,
                initial=matricula.plan_pago.numero_cuotas,
                help_text="Número de cuotas para la colegiatura"
            )
            nuevo_monto_colegiatura = forms.DecimalField(
                label="Nuevo monto de colegiatura",
                max_digits=10, decimal_places=2,
                initial=matricula.plan_pago.monto_colegiatura,
                help_text="Monto total de la colegiatura"
            )
            motivo_reestructuracion = forms.CharField(
                label="Motivo de la reestructuración",
                widget=forms.Textarea(attrs={'rows': 4}),
                required=True,
                help_text="Explique el motivo de la reestructuración del plan"
            )
            constancia_reestructuracion = forms.FileField(
                label="Constancia de reestructuración",
                required=False,
                help_text="Documento que justifica la reestructuración (opcional)"
            )
        
        if request.method == 'POST':
            form = ReestructurarPlanForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    plan = matricula.plan_pago
                    cambios = plan.reestructurar_plan(
                        nuevo_numero_cuotas=form.cleaned_data['nuevo_numero_cuotas'],
                        nuevo_monto_colegiatura=form.cleaned_data['nuevo_monto_colegiatura'],
                        motivo_reestructuracion=form.cleaned_data['motivo_reestructuracion'],
                        constancia_reestructuracion=form.cleaned_data.get('constancia_reestructuracion')
                    )
                    
                    if cambios:
                        messages.success(
                            request, 
                            f"Plan reestructurado exitosamente para {matricula.estudiante}. "
                            f"Cambios: {', '.join(cambios)}. "
                            f"Se regeneraron las cuotas pendientes."
                        )
                    else:
                        messages.info(request, "No se realizaron cambios en el plan.")
                    
                    return redirect('admin:modulo_pagos_matricula_changelist')
                except Exception as e:
                    messages.error(request, f"Error al reestructurar el plan: {str(e)}")
        else:
            form = ReestructurarPlanForm()
        
        context = {
            'title': f'Reestructurar Plan de Pago - {matricula.estudiante}',
            'matricula': matricula,
            'plan': matricula.plan_pago,
            'form': form,
            'cuotas_pagadas': matricula.plan_pago.cuotas.filter(estado='pagado').count(),
            'cuotas_pendientes': matricula.plan_pago.cuotas.exclude(estado='pagado').count(),
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/modulo_pagos/reestructurar_plan.html', context)
