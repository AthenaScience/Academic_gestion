from django.db import models
from modulos.modulo_estudiantes.models import Estudiante
from modulos.modulo_certificados.models import Evento, CostoMiscelaneo
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class InstitucionFinanciera(models.Model):
    """
    Modelo para gestionar las instituciones financieras donde se realizan los pagos
    """
    TIPO_INSTITUCION_CHOICES = [
        ('banco', 'Banco'),
        ('cooperativa', 'Cooperativa'),
        ('financiera', 'Financiera'),
        ('otro', 'Otro'),
    ]
    
    codigo = models.CharField(max_length=10, unique=True, help_text="Código único de la institución")
    nombre = models.CharField(max_length=100, help_text="Nombre de la institución financiera")
    tipo_institucion = models.CharField(max_length=20, choices=TIPO_INSTITUCION_CHOICES, default='banco')
    activo = models.BooleanField(default=True, help_text="¿La institución está activa?")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Institución Financiera'
        verbose_name_plural = 'Instituciones Financieras'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que el código sea único
        if InstitucionFinanciera.objects.filter(codigo=self.codigo).exclude(id=self.id).exists():
            raise ValidationError("Ya existe una institución con este código")

class PlanPago(models.Model):
    """
    Plan de pago unificado por matrícula.
    Reemplaza PlanPagoColegiatura y PlanPagoPersonalizado.
    """
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='planes_pago')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='planes_pago')
    numero_cuotas = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])
    monto_colegiatura = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto total de la colegiatura a prorratear en cuotas"
    )
    usa_monto_personalizado = models.BooleanField(default=False)
    aplicar_beca_descuentos = models.BooleanField(default=True)
    # Asociación opcional de becas/descuentos al plan
    # (se mantiene compatibilidad permitiendo cálculo al vuelo)
    # Definidos al final del archivo: usar string para evitar orden de definición
    becas = models.ManyToManyField('Beca', blank=True, related_name='planes_pago')
    descuentos = models.ManyToManyField('Descuento', blank=True, related_name='planes_pago')
    
    # Campos para convenios de pago
    tiene_convenio = models.BooleanField(
        default=False, 
        help_text="Indica si tiene un convenio de pago especial"
    )
    constancia_convenio = models.FileField(
        upload_to='convenios_pago/', 
        blank=True, 
        null=True,
        help_text="Documento de constancia del convenio de pago"
    )
    motivo_convenio = models.TextField(
        blank=True,
        help_text="Motivo del convenio de pago"
    )
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('estudiante', 'evento')
        verbose_name = 'Plan de Pago'
        verbose_name_plural = 'Planes de Pago'

    def __str__(self):
        return f"Plan de pago de {self.estudiante} en {self.evento} ({self.numero_cuotas} cuotas)"

    def generar_cuotas(self):
        """Genera todas las cuotas desde cero según configuración actual."""
        from datetime import timedelta
        # Eliminar pendientes antes de recalcular (se asume uso en creación inicial)
        self.cuotas.filter(estado__in=['pendiente', 'atrasado']).delete()

        # Calcular monto por cuota (ajustar a dos decimales y residuo en última)
        monto_total = self.monto_colegiatura
        cuotas_a_generar = self.numero_cuotas
        if cuotas_a_generar <= 0:
            return []

        monto_base = (monto_total / cuotas_a_generar).quantize(Decimal('0.01'))
        montos = [monto_base for _ in range(cuotas_a_generar)]
        diferencia = monto_total - sum(montos)
        # Ajustar la última cuota con el redondeo pendiente
        if diferencia != Decimal('0.00'):
            montos[-1] = (montos[-1] + diferencia).quantize(Decimal('0.01'))

        fecha_inicio = self.evento.fecha_inicio
        cuotas = []
        for idx, monto in enumerate(montos, start=1):
            fecha_venc = fecha_inicio + timedelta(days=30 * (idx - 1))
            cuota = Cuota.objects.create(
                plan_pago=self,
                numero_cuota=idx,
                monto=monto,
                fecha_vencimiento=fecha_venc,
                estado='pendiente',
            )
            cuotas.append(cuota)
        return cuotas

    def regenerar_cuotas_pendientes(self):
        """
        Regenera únicamente las cuotas pendientes/atrasadas acorde a
        numero_cuotas y monto_colegiatura actuales. Mantiene cuotas pagadas.
        """
        from datetime import timedelta
        cuotas_pagadas = list(self.cuotas.filter(estado='pagado').order_by('numero_cuota'))
        num_pagadas = len(cuotas_pagadas)
        # Borrar pendientes/atrasadas
        self.cuotas.exclude(estado='pagado').delete()

        # Calcular monto restante y cuotas restantes
        monto_pagado_teorico = sum((c.monto for c in cuotas_pagadas), Decimal('0.00'))
        monto_restante = (self.monto_colegiatura - monto_pagado_teorico).quantize(Decimal('0.01'))
        cuotas_restantes = max(self.numero_cuotas - num_pagadas, 0)
        if cuotas_restantes == 0 or monto_restante <= Decimal('0.00'):
            return []

        monto_base = (monto_restante / cuotas_restantes).quantize(Decimal('0.01'))
        montos = [monto_base for _ in range(cuotas_restantes)]
        diferencia = monto_restante - sum(montos)
        if diferencia != Decimal('0.00'):
            montos[-1] = (montos[-1] + diferencia).quantize(Decimal('0.01'))

        # Continuar numeración y calendario mensual desde hoy
        from django.utils import timezone
        fecha_base = timezone.now().date()
        nuevas = []
        for offset, monto in enumerate(montos, start=1):
            fecha_venc = fecha_base + timedelta(days=30 * (offset - 1))
            cuota = Cuota.objects.create(
                plan_pago=self,
                numero_cuota=num_pagadas + offset,
                monto=monto,
                fecha_vencimiento=fecha_venc,
                estado='pendiente',
            )
            nuevas.append(cuota)
        return nuevas

    def reestructurar_plan(self, nuevo_numero_cuotas=None, nuevo_monto_colegiatura=None, motivo_reestructuracion=None, constancia_reestructuracion=None):
        """
        Reestructura el plan de pago con nuevos parámetros, manteniendo cuotas pagadas.
        Útil para cambios a mitad de curso.
        """
        cambios_realizados = []
        
        if nuevo_numero_cuotas and nuevo_numero_cuotas != self.numero_cuotas:
            self.numero_cuotas = nuevo_numero_cuotas
            cambios_realizados.append(f"Número de cuotas: {nuevo_numero_cuotas}")
        
        if nuevo_monto_colegiatura and nuevo_monto_colegiatura != self.monto_colegiatura:
            self.monto_colegiatura = nuevo_monto_colegiatura
            cambios_realizados.append(f"Monto colegiatura: ${nuevo_monto_colegiatura}")
        
        if motivo_reestructuracion:
            # Agregar al motivo de convenio existente o crear uno nuevo
            if self.motivo_convenio:
                self.motivo_convenio += f"\n\nReestructuración: {motivo_reestructuracion}"
            else:
                self.motivo_convenio = f"Reestructuración: {motivo_reestructuracion}"
            self.tiene_convenio = True
        
        if constancia_reestructuracion:
            self.constancia_convenio = constancia_reestructuracion
            self.tiene_convenio = True
        
        if cambios_realizados:
            self.save()  # Esto triggereará regenerar_cuotas_pendientes automáticamente
            return cambios_realizados
        
        return []

    def save(self, *args, **kwargs):
        # Detectar cambios relevantes para regenerar cuotas pendientes
        if self.pk is not None:
            prev = PlanPago.objects.filter(pk=self.pk).only('numero_cuotas', 'monto_colegiatura').first()
        else:
            prev = None
        super().save(*args, **kwargs)
        if prev and (prev.numero_cuotas != self.numero_cuotas or prev.monto_colegiatura != self.monto_colegiatura):
            self.regenerar_cuotas_pendientes()

class Cuota(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('atrasado', 'Atrasado'),
        ('cancelado', 'Cancelado'),
    ]

    plan_pago = models.ForeignKey(
        'PlanPago',
        on_delete=models.CASCADE,
        related_name='cuotas'
    )
    
    numero_cuota = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago = models.DateField(null=True, blank=True)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)
    
    # Campos para el comprobante de pago
    comprobante = models.ImageField(upload_to='comprobantes_cuotas/', blank=True, null=True)
    institucion_financiera = models.ForeignKey(
        InstitucionFinanciera, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Institución financiera donde se realizó el pago"
    )
    codigo_comprobante = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Código de comprobante de la institución financiera"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = [
            ('plan_pago', 'numero_cuota'),
        ]
        verbose_name = 'Cuota'
        verbose_name_plural = 'Cuotas'

    def __str__(self):
        monto_pendiente = self.monto - (self.monto_pagado or Decimal('0.00'))
        if monto_pendiente > 0:
            return f"Cuota {self.numero_cuota} - ${monto_pendiente} ({self.get_estado_display()})"
        else:
            return f"Cuota {self.numero_cuota} - ${self.monto} (Pagada)"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar unicidad del número de cuota dentro del plan
        if Cuota.objects.filter(
            plan_pago=self.plan_pago,
            numero_cuota=self.numero_cuota
        ).exclude(id=self.id).exists():
            raise ValidationError("Ya existe una cuota con este número en el plan")
    
    @property
    def estudiante(self):
        """Retorna el estudiante asociado a la cuota"""
        return self.plan_pago.estudiante
    
    @property
    def evento(self):
        """Retorna el evento asociado a la cuota"""
        return self.plan_pago.evento

class Pago(models.Model):
    TIPO_PAGO_CHOICES = [
        ('matricula', 'Matrícula'),
        ('cuota_individual', 'Cuota Individual'),
        ('colegiatura_parcial', 'Colegiatura Parcial'),
        ('colegiatura_total', 'Colegiatura Total'),
        ('certificado', 'Certificado'),
        ('miscelaneo', 'Misceláneo'),
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta de Crédito'),
        ('cheque', 'Cheque'),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='pagos')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, null=True, blank=True)
    tipo_pago = models.CharField(max_length=25, choices=TIPO_PAGO_CHOICES)
    cuota = models.ForeignKey(Cuota, on_delete=models.CASCADE, related_name='pagos', null=True, blank=True)
    costo_miscelaneo = models.ForeignKey(CostoMiscelaneo, on_delete=models.SET_NULL, null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Campos adicionales para pagos de colegiatura
    cuotas_aplicadas = models.ManyToManyField(
        Cuota, 
        through='PagoCuotaAplicada', 
        related_name='pagos_aplicados',
        blank=True,
        help_text="Cuotas a las que se aplica este pago (para pagos parciales/totales)"
    )
    monto_aplicado_colegiatura = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Monto aplicado específicamente a colegiatura (para pagos parciales/totales)"
    )
    fecha_pago = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    comprobante = models.ImageField(upload_to='comprobantes_pago/', blank=True, null=True)
    observaciones = models.TextField(blank=True)
    numero_transaccion = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Pago de {self.estudiante} - {self.monto} ({self.get_tipo_pago_display()}) - {self.evento}"
    
    def es_pago_colegiatura(self):
        """Verifica si es un pago relacionado con colegiatura"""
        return self.tipo_pago in ['cuota_individual', 'colegiatura_parcial', 'colegiatura_total']
    
    def aplicar_a_cuotas(self, cuotas_ids=None):
        """Aplica el pago a las cuotas especificadas o automáticamente según el tipo"""
        if not self.es_pago_colegiatura():
            return
        
        plan = PlanPago.objects.filter(
            estudiante=self.estudiante, evento=self.evento
        ).first()
        
        if not plan:
            return
        
        monto_disponible = self.monto_aplicado_colegiatura or self.monto
        
        if self.tipo_pago == 'cuota_individual' and self.cuota:
            # Pago de cuota individual
            self._aplicar_a_cuota_individual(self.cuota, monto_disponible)
        elif self.tipo_pago in ['colegiatura_parcial', 'colegiatura_total']:
            # Pago parcial o total
            if cuotas_ids:
                cuotas = Cuota.objects.filter(id__in=cuotas_ids, plan_pago=plan)
            else:
                # Aplicar automáticamente a cuotas pendientes en orden
                cuotas = Cuota.objects.filter(
                    plan_pago=plan, estado='pendiente'
                ).order_by('numero_cuota')
            
            self._aplicar_a_multiples_cuotas(cuotas, monto_disponible)
    
    def _aplicar_a_cuota_individual(self, cuota, monto):
        """Aplica pago a una cuota individual"""
        monto_pendiente = cuota.monto - (cuota.monto_pagado or Decimal('0.00'))
        monto_aplicar = min(monto, monto_pendiente)
        
        if monto_aplicar > 0:
            PagoCuotaAplicada.objects.create(
                pago=self,
                cuota=cuota,
                monto_aplicado=monto_aplicar
            )
            
            cuota.monto_pagado = (cuota.monto_pagado or Decimal('0.00')) + monto_aplicar
            if cuota.monto_pagado >= cuota.monto:
                cuota.estado = 'pagada'
                cuota.fecha_pago = self.fecha_pago.date()
            cuota.save()
    
    def _aplicar_a_multiples_cuotas(self, cuotas, monto_total):
        """Aplica pago a múltiples cuotas en orden"""
        monto_restante = monto_total
        
        for cuota in cuotas:
            if monto_restante <= 0:
                break
                
            monto_pendiente = cuota.monto - (cuota.monto_pagado or Decimal('0.00'))
            monto_aplicar = min(monto_restante, monto_pendiente)
            
            if monto_aplicar > 0:
                PagoCuotaAplicada.objects.create(
                    pago=self,
                    cuota=cuota,
                    monto_aplicado=monto_aplicar
                )
                
                cuota.monto_pagado = (cuota.monto_pagado or Decimal('0.00')) + monto_aplicar
                if cuota.monto_pagado >= cuota.monto:
                    cuota.estado = 'pagada'
                    cuota.fecha_pago = self.fecha_pago.date()
                cuota.save()
                
                monto_restante -= monto_aplicar
    
    def save(self, *args, **kwargs):
        """Sobrescribir save para aplicar automáticamente pagos a cuotas"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Solo aplicar a cuotas si es un pago nuevo de colegiatura
        if is_new and self.es_pago_colegiatura():
            cuotas_ids_prefijadas = getattr(self, '_cuotas_ids_prefijadas', None)
            self.aplicar_a_cuotas(cuotas_ids=cuotas_ids_prefijadas)


class PagoCuotaAplicada(models.Model):
    """Modelo intermedio para tracking de montos aplicados a cuotas específicas"""
    pago = models.ForeignKey(Pago, on_delete=models.CASCADE, related_name='aplicaciones_cuotas')
    cuota = models.ForeignKey(Cuota, on_delete=models.CASCADE, related_name='pagos_aplicados_detalle')
    monto_aplicado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monto específico aplicado a esta cuota desde este pago"
    )
    fecha_aplicacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['pago', 'cuota']
        verbose_name = "Aplicación de Pago a Cuota"
        verbose_name_plural = "Aplicaciones de Pago a Cuotas"
    
    def __str__(self):
        return f"${self.monto_aplicado} del Pago {self.pago.id} → Cuota {self.cuota.numero_cuota}"


class PagoCuota(models.Model):
    """
    Modelo para registrar cada pago específico de una cuota
    """
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta de Crédito'),
        ('cheque', 'Cheque'),
        ('deposito', 'Depósito'),
        ('pago_movil', 'Pago Móvil'),
    ]
    
    cuota = models.ForeignKey(Cuota, on_delete=models.CASCADE, related_name='pagos_cuota')
    monto_pagado = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monto pagado en esta transacción"
    )
    fecha_pago = models.DateField(help_text="Fecha en que se realizó el pago")
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    
    # Información del comprobante
    institucion_financiera = models.ForeignKey(
        InstitucionFinanciera, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Institución financiera donde se realizó el pago"
    )
    codigo_comprobante = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Código de comprobante de la institución financiera"
    )
    comprobante = models.ImageField(
        upload_to='comprobantes_pago_cuotas/', 
        blank=True, 
        null=True,
        help_text="Imagen del comprobante de pago"
    )
    
    # Información adicional
    observaciones = models.TextField(blank=True, help_text="Observaciones adicionales del pago")
    numero_transaccion = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Número de transacción interno o de la institución"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pago de Cuota'
        verbose_name_plural = 'Pagos de Cuotas'
        ordering = ['-fecha_pago', '-fecha_creacion']
    
    def __str__(self):
        return f"Pago de cuota {self.cuota.numero_cuota} - {self.cuota.estudiante} - ${self.monto_pagado}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que el monto pagado no exceda el monto de la cuota
        if self.monto_pagado > self.cuota.monto:
            raise ValidationError(
                f"El monto pagado (${self.monto_pagado}) no puede exceder el monto de la cuota (${self.cuota.monto})"
            )
        
        # Validar que la fecha de pago no sea futura
        from django.utils import timezone
        if self.fecha_pago > timezone.now().date():
            raise ValidationError("La fecha de pago no puede ser futura")
    
    def save(self, *args, **kwargs):
        # Actualizar el estado de la cuota si se paga completamente
        if self.monto_pagado >= self.cuota.monto:
            self.cuota.estado = 'pagado'
            self.cuota.fecha_pago = self.fecha_pago
            self.cuota.monto_pagado = self.monto_pagado
            self.cuota.save()
        
        super().save(*args, **kwargs)
    
    @property
    def estudiante(self):
        """Retorna el estudiante asociado al pago"""
        return self.cuota.estudiante
    
    @property
    def evento(self):
        """Retorna el evento asociado al pago"""
        return self.cuota.evento

class EstadoPagosEvento(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, null=True, blank=True)
    matricula_pagada = models.BooleanField(default=False)
    certificado_pagado = models.BooleanField(default=False)
    colegiatura_al_dia = models.BooleanField(default=False)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('estudiante', 'evento')

    def __str__(self):
        return f"Estado de pagos de {self.estudiante} en {self.evento}"

class Matricula(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva'),
        ('pendiente', 'Pendiente'),
        ('cancelada', 'Cancelada'),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='matriculas')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, null=True, blank=True)
    plan_pago = models.ForeignKey('PlanPago', on_delete=models.CASCADE, related_name='matriculas', null=True, blank=True)
    
    # Comprobante de matrícula
    comprobante_matricula = models.FileField(
        upload_to='comprobantes_matricula/', 
        blank=True, 
        null=True,
        help_text="Comprobante de matrícula del estudiante"
    )
    
    fecha_matricula = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True)

    class Meta:
        unique_together = ('estudiante', 'evento')

    def __str__(self):
        return f"Matrícula de {self.estudiante} en {self.evento}"

class Beca(models.Model):
    TIPO_BECA_CHOICES = [
        ('porcentual', 'Porcentual'),
        ('monto_fijo', 'Monto Fijo'),
        ('combinada', 'Combinada'),
    ]
    
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva'),
        ('expirada', 'Expirada'),
        ('cancelada', 'Cancelada'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='becas')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='becas')
    nombre_beca = models.CharField(max_length=100, help_text="Nombre de la beca (ej: Beca Excelencia, Beca Deportiva)")
    tipo_beca = models.CharField(max_length=20, choices=TIPO_BECA_CHOICES, default='porcentual')
    
    # Para becas porcentuales
    porcentaje_descuento = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        null=True, 
        blank=True,
        help_text="Porcentaje de descuento (0-100)"
    )
    
    # Para becas de monto fijo
    monto_descuento = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        null=True, 
        blank=True,
        help_text="Monto fijo de descuento"
    )
    
    # Aplicación de la beca
    aplica_matricula = models.BooleanField(default=True, help_text="¿Aplica descuento a la matrícula?")
    aplica_colegiatura = models.BooleanField(default=True, help_text="¿Aplica descuento a la colegiatura?")
    aplica_certificado = models.BooleanField(default=False, help_text="¿Aplica descuento al certificado?")
    
    # Fechas y estado
    fecha_inicio = models.DateField(help_text="Fecha desde cuando aplica la beca")
    fecha_fin = models.DateField(help_text="Fecha hasta cuando aplica la beca")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    
    # Información adicional
    motivo = models.TextField(help_text="Motivo de la beca")
    documentos_soporte = models.FileField(upload_to='documentos_becas/', blank=True, null=True)
    aprobado_por = models.CharField(max_length=100, blank=True, help_text="Persona que aprobó la beca")
    fecha_aprobacion = models.DateTimeField(auto_now_add=True)
    
    # Campos calculados
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('estudiante', 'evento', 'nombre_beca')
        verbose_name = 'Beca'
        verbose_name_plural = 'Becas'
    
    def __str__(self):
        return f"{self.nombre_beca} - {self.estudiante} en {self.evento}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que al menos un campo de descuento esté lleno
        if not self.porcentaje_descuento and not self.monto_descuento:
            raise ValidationError("Debe especificar un porcentaje o monto de descuento")
        
        # Validar que al menos un campo de aplicación esté marcado
        if not any([self.aplica_matricula, self.aplica_colegiatura, self.aplica_certificado]):
            raise ValidationError("Debe seleccionar al menos un tipo de pago para aplicar la beca")
    
    @property
    def esta_activa(self):
        """Verifica si la beca está activa y vigente"""
        from django.utils import timezone
        hoy = timezone.now().date()
        return (
            self.estado == 'activa' and 
            self.fecha_inicio <= hoy <= self.fecha_fin
        )
    
    def calcular_descuento(self, monto_original, tipo_pago):
        """Calcula el descuento aplicable según el tipo de pago"""
        if not self.esta_activa:
            return Decimal('0.00')
        
        # Verificar si aplica al tipo de pago
        if tipo_pago == 'matricula' and not self.aplica_matricula:
            return Decimal('0.00')
        elif tipo_pago == 'colegiatura' and not self.aplica_colegiatura:
            return Decimal('0.00')
        elif tipo_pago == 'certificado' and not self.aplica_certificado:
            return Decimal('0.00')
        
        # Calcular descuento
        if self.tipo_beca == 'porcentual' and self.porcentaje_descuento:
            descuento = monto_original * (self.porcentaje_descuento / Decimal('100.00'))
        elif self.tipo_beca == 'monto_fijo' and self.monto_descuento:
            descuento = min(self.monto_descuento, monto_original)
        else:
            descuento = Decimal('0.00')
        
        return descuento.quantize(Decimal('0.01'))

class Descuento(models.Model):
    TIPO_DESCUENTO_CHOICES = [
        ('porcentual', 'Porcentual'),
        ('monto_fijo', 'Monto Fijo'),
    ]
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('expirado', 'Expirado'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='descuentos')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='descuentos')
    nombre_descuento = models.CharField(max_length=100, help_text="Nombre del descuento")
    tipo_descuento = models.CharField(max_length=20, choices=TIPO_DESCUENTO_CHOICES, default='porcentual')
    
    # Para descuentos porcentuales
    porcentaje_descuento = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        null=True, 
        blank=True
    )
    
    # Para descuentos de monto fijo
    monto_descuento = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        null=True, 
        blank=True
    )
    
    # Aplicación del descuento
    aplica_matricula = models.BooleanField(default=True)
    aplica_colegiatura = models.BooleanField(default=True)
    aplica_certificado = models.BooleanField(default=False)
    
    # Fechas y estado
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    
    # Información adicional
    motivo = models.TextField(help_text="Motivo del descuento")
    codigo_promocional = models.CharField(max_length=20, blank=True, help_text="Código promocional si aplica")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('estudiante', 'evento', 'nombre_descuento')
        verbose_name = 'Descuento'
        verbose_name_plural = 'Descuentos'
    
    def __str__(self):
        return f"{self.nombre_descuento} - {self.estudiante} en {self.evento}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que al menos un campo de descuento esté lleno
        if not self.porcentaje_descuento and not self.monto_descuento:
            raise ValidationError("Debe especificar un porcentaje o monto de descuento")
    
    @property
    def esta_activo(self):
        """Verifica si el descuento está activo y vigente"""
        from django.utils import timezone
        hoy = timezone.now().date()
        return (
            self.estado == 'activo' and 
            self.fecha_inicio <= hoy <= self.fecha_fin
        )
    
    def calcular_descuento(self, monto_original, tipo_pago):
        """Calcula el descuento aplicable según el tipo de pago"""
        if not self.esta_activo:
            return Decimal('0.00')
        
        # Verificar si aplica al tipo de pago
        if tipo_pago == 'matricula' and not self.aplica_matricula:
            return Decimal('0.00')
        elif tipo_pago == 'colegiatura' and not self.aplica_colegiatura:
            return Decimal('0.00')
        elif tipo_pago == 'certificado' and not self.aplica_certificado:
            return Decimal('0.00')
        
        # Calcular descuento
        if self.tipo_descuento == 'porcentual' and self.porcentaje_descuento:
            descuento = monto_original * (self.porcentaje_descuento / Decimal('100.00'))
        elif self.tipo_descuento == 'monto_fijo' and self.monto_descuento:
            descuento = min(self.monto_descuento, monto_original)
        else:
            descuento = Decimal('0.00')
        
        return descuento.quantize(Decimal('0.01'))
