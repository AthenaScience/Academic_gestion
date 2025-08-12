from rest_framework import serializers
from .models import (
    PlanPago,
    Cuota,
    Pago,
    PagoCuota,
    InstitucionFinanciera,
    EstadoPagosEvento,
    Matricula,
    Beca,
    Descuento
)
from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento

class PlanPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanPago
        fields = [
            'id', 'estudiante', 'evento', 'numero_cuotas', 'monto_colegiatura',
            'usa_monto_personalizado', 'aplicar_beca_descuentos', 'becas', 'descuentos',
            'tiene_convenio', 'constancia_convenio', 'motivo_convenio',
            'activo', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']

class PlanPagoNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanPago
        fields = [
            'numero_cuotas', 'monto_colegiatura', 'usa_monto_personalizado',
            'aplicar_beca_descuentos', 'becas', 'descuentos',
            'tiene_convenio', 'constancia_convenio', 'motivo_convenio'
        ]

class InstitucionFinancieraSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitucionFinanciera
        fields = ['id', 'codigo', 'nombre', 'tipo_institucion', 'activo', 'fecha_creacion']
        read_only_fields = ['id', 'fecha_creacion']

class CuotaSerializer(serializers.ModelSerializer):
    plan_pago_nombre = serializers.CharField(source='plan_pago.__str__', read_only=True)
    estudiante_nombre = serializers.CharField(source='estudiante.nombres', read_only=True)
    evento_nombre = serializers.CharField(source='evento.nombre', read_only=True)
    institucion_financiera_nombre = serializers.CharField(source='institucion_financiera.nombre', read_only=True)
    
    class Meta:
        model = Cuota
        fields = [
            'id', 'plan_pago', 'numero_cuota', 
            'monto', 'fecha_vencimiento', 'estado', 'fecha_pago', 'monto_pagado',
            'observaciones', 'comprobante', 'institucion_financiera', 'codigo_comprobante',
            'fecha_creacion', 'fecha_modificacion', 'plan_pago_nombre',
            'estudiante_nombre', 'evento_nombre',
            'institucion_financiera_nombre'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']
    
    def validate(self, data):
        # Validar que el número de cuota sea positivo
        if data.get('numero_cuota', 1) < 1:
            raise serializers.ValidationError("El número de cuota debe ser mayor o igual a 1")
        
        return data

class PagoCuotaSerializer(serializers.ModelSerializer):
    cuota_nombre = serializers.CharField(source='cuota.__str__', read_only=True)
    estudiante_nombre = serializers.CharField(source='estudiante.nombres', read_only=True)
    evento_nombre = serializers.CharField(source='evento.nombre', read_only=True)
    institucion_financiera_nombre = serializers.CharField(source='institucion_financiera.nombre', read_only=True)
    
    class Meta:
        model = PagoCuota
        fields = [
            'id', 'cuota', 'monto_pagado', 'fecha_pago', 'metodo_pago',
            'institucion_financiera', 'codigo_comprobante', 'comprobante',
            'observaciones', 'numero_transaccion', 'fecha_creacion', 'fecha_modificacion',
            'cuota_nombre', 'estudiante_nombre', 'evento_nombre', 'institucion_financiera_nombre'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']
    
    def validate(self, data):
        cuota = data.get('cuota')
        monto_pagado = data.get('monto_pagado')
        
        if cuota and monto_pagado:
            if monto_pagado > cuota.monto:
                raise serializers.ValidationError(
                    f"El monto pagado (${monto_pagado}) no puede exceder el monto de la cuota (${cuota.monto})"
                )
        
        return data

class PagoSerializer(serializers.ModelSerializer):
    cuotas_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False,
        help_text="IDs de cuotas (pendientes) a las que aplicar el pago parcial/total."
    )
    class Meta:
        model = Pago
        fields = ['id', 'estudiante', 'evento', 'tipo_pago', 'cuota', 'monto', 'fecha_pago', 'comprobante', 'metodo_pago', 'observaciones', 'cuotas_ids']
        read_only_fields = ['id']

    def validate(self, data):
        """
        Validar que el monto del pago sea correcto según el tipo de pago y el evento
        """
        estudiante = data.get('estudiante')
        evento = data.get('evento')
        tipo_pago = data.get('tipo_pago')
        monto = data.get('monto')

        # Validaciones base por tipo de pago
        if tipo_pago == 'miscelaneo':
            # Para misceláneos: evento es opcional y se requiere descripción
            if not all([estudiante, tipo_pago, monto]):
                raise serializers.ValidationError("Faltan campos requeridos (estudiante, monto)")
            if not data.get('observaciones'):
                raise serializers.ValidationError("Para pagos misceláneos debes especificar una descripción en 'observaciones'")
            return data
        else:
            if not all([estudiante, evento, tipo_pago, monto]):
                raise serializers.ValidationError("Faltan campos requeridos")

        # Validar que el estudiante esté matriculado en el evento (via M2M o Matricula)
        from modulos.modulo_pagos.models import Matricula as MatriculaModel
        matriculado = (
            evento in estudiante.eventos_matriculados.all()
            or MatriculaModel.objects.filter(estudiante=estudiante, evento=evento).exists()
        )
        if not matriculado:
            raise serializers.ValidationError("El estudiante no está matriculado en este evento")

        # Validar el monto según el tipo de pago
        if tipo_pago == 'matricula':
            if monto != evento.costo_matricula:
                raise serializers.ValidationError(f"El monto debe ser igual al costo de matrícula: {evento.costo_matricula}")
        elif tipo_pago == 'certificado':
            if monto != evento.costo_certificado:
                raise serializers.ValidationError(f"El monto debe ser igual al costo del certificado: {evento.costo_certificado}")
        elif tipo_pago in ['cuota_individual', 'colegiatura_parcial', 'colegiatura_total']:
            # Verificar si existe un plan de pago
            plan_pago = PlanPago.objects.filter(estudiante=estudiante, evento=evento).first()
            if not plan_pago:
                raise serializers.ValidationError("No existe un plan de pago para este estudiante y evento")
            
            if tipo_pago == 'cuota_individual':
                # Para cuota individual, verificar que hay cuotas pendientes y el campo cuota está presente
                cuota = data.get('cuota')
                if not cuota:
                    raise serializers.ValidationError("Debe especificar la cuota a pagar para pagos individuales")
                
                # Verificar que la cuota pertenece al plan del estudiante
                if cuota.plan_pago != plan_pago:
                    raise serializers.ValidationError("La cuota seleccionada no pertenece al plan de pago del estudiante")
                
                # Verificar que la cuota está pendiente
                if cuota.estado != 'pendiente':
                    raise serializers.ValidationError("La cuota seleccionada ya está pagada")
                
                # Verificar que el monto no excede lo pendiente de la cuota
                monto_pendiente = cuota.monto - (cuota.monto_pagado or 0)
                if monto > monto_pendiente:
                    raise serializers.ValidationError(f"El monto no puede exceder lo pendiente de la cuota: ${monto_pendiente}")
            
            elif tipo_pago in ['colegiatura_parcial', 'colegiatura_total']:
                # Verificar que hay cuotas pendientes
                cuotas_pendientes = Cuota.objects.filter(plan_pago=plan_pago, estado='pendiente')
                
                if not cuotas_pendientes.exists():
                    raise serializers.ValidationError("No hay cuotas pendientes para este estudiante en este evento")
                
                # Para pago total, verificar que el monto cubra todas las cuotas pendientes
                if tipo_pago == 'colegiatura_total':
                    total_pendiente = sum(c.monto - (c.monto_pagado or 0) for c in cuotas_pendientes)
                    if monto < total_pendiente:
                        raise serializers.ValidationError(f"Para pago total, el monto debe ser al menos ${total_pendiente}")
                
                # Para pago parcial, el monto debe ser positivo y menor que el total pendiente
                elif tipo_pago == 'colegiatura_parcial':
                    total_pendiente = sum(c.monto - (c.monto_pagado or 0) for c in cuotas_pendientes)
                    if monto >= total_pendiente:
                        raise serializers.ValidationError("Para pago parcial, use 'colegiatura_total' si va a pagar todo lo pendiente")
                # Validar cuotas_ids si vienen explícitas
                cuotas_ids = self.initial_data.get('cuotas_ids')
                if cuotas_ids:
                    qs = Cuota.objects.filter(id__in=cuotas_ids, plan_pago=plan_pago, estado='pendiente')
                    if qs.count() != len(set(cuotas_ids)):
                        raise serializers.ValidationError("Alguna cuota en 'cuotas_ids' no pertenece al plan o no está pendiente")

        return data

    def create(self, validated_data):
        cuotas_ids = self.initial_data.get('cuotas_ids')
        pago = super().create(validated_data)
        if pago.es_pago_colegiatura() and cuotas_ids:
            setattr(pago, '_cuotas_ids_prefijadas', cuotas_ids)
            pago.aplicar_a_cuotas(cuotas_ids=cuotas_ids)
        return pago

class EstadoPagosEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoPagosEvento
        fields = ['id', 'estudiante', 'evento', 'matricula_pagada', 'certificado_pagado', 'colegiatura_al_dia']
        read_only_fields = ['id']

class MatriculaSerializer(serializers.ModelSerializer):
    plan_de_pago = PlanPagoNestedSerializer(write_only=True, required=False)
    class Meta:
        model = Matricula
        fields = [
            'id', 'estudiante', 'evento', 'plan_pago', 'plan_de_pago', 
            'comprobante_matricula', 'fecha_matricula', 'estado', 'observaciones'
        ]
        read_only_fields = ['id'] 

    def create(self, validated_data):
        plan_de_pago_data = validated_data.pop('plan_de_pago', None)
        matricula = super().create(validated_data)
        if plan_de_pago_data:
            # Si no es monto personalizado, usar el costo de colegiatura del evento
            if not plan_de_pago_data.get('usa_monto_personalizado', False):
                plan_de_pago_data['monto_colegiatura'] = matricula.evento.costo_colegiatura
            
            plan = PlanPago.objects.create(
                estudiante=matricula.estudiante,
                evento=matricula.evento,
                **plan_de_pago_data
            )
            matricula.plan_pago = plan
            matricula.save(update_fields=['plan_pago'])
            plan.generar_cuotas()
        return matricula

class BecaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombres', read_only=True)
    estudiante_apellidos = serializers.CharField(source='estudiante.apellidos', read_only=True)
    evento_nombre = serializers.CharField(source='evento.nombre', read_only=True)
    esta_activa = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Beca
        fields = [
            'id', 'estudiante', 'evento', 'nombre_beca', 'tipo_beca',
            'porcentaje_descuento', 'monto_descuento',
            'aplica_matricula', 'aplica_colegiatura', 'aplica_certificado',
            'fecha_inicio', 'fecha_fin', 'estado', 'motivo',
            'documentos_soporte', 'aprobado_por', 'fecha_aprobacion',
            'fecha_creacion', 'fecha_modificacion',
            'estudiante_nombre', 'estudiante_apellidos', 'evento_nombre', 'esta_activa'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion', 'fecha_aprobacion']
    
    def validate(self, data):
        # Validar que al menos un campo de descuento esté lleno
        if not data.get('porcentaje_descuento') and not data.get('monto_descuento'):
            raise serializers.ValidationError("Debe especificar un porcentaje o monto de descuento")
        
        # Validar que al menos un campo de aplicación esté marcado
        if not any([
            data.get('aplica_matricula', False),
            data.get('aplica_colegiatura', False),
            data.get('aplica_certificado', False)
        ]):
            raise serializers.ValidationError("Debe seleccionar al menos un tipo de pago para aplicar la beca")
        
        return data

class DescuentoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombres', read_only=True)
    estudiante_apellidos = serializers.CharField(source='estudiante.apellidos', read_only=True)
    evento_nombre = serializers.CharField(source='evento.nombre', read_only=True)
    esta_activo = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Descuento
        fields = [
            'id', 'estudiante', 'evento', 'nombre_descuento', 'tipo_descuento',
            'porcentaje_descuento', 'monto_descuento',
            'aplica_matricula', 'aplica_colegiatura', 'aplica_certificado',
            'fecha_inicio', 'fecha_fin', 'estado', 'motivo', 'codigo_promocional',
            'fecha_creacion', 'fecha_modificacion',
            'estudiante_nombre', 'estudiante_apellidos', 'evento_nombre', 'esta_activo'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']
    
    def validate(self, data):
        # Validar que al menos un campo de descuento esté lleno
        if not data.get('porcentaje_descuento') and not data.get('monto_descuento'):
            raise serializers.ValidationError("Debe especificar un porcentaje o monto de descuento")
        
        return data 