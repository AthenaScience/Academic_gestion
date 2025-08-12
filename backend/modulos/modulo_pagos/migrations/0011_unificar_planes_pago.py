from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def migrate_planes_pago_forward(apps, schema_editor):
    PlanPago = apps.get_model('modulo_pagos', 'PlanPago')
    Cuota = apps.get_model('modulo_pagos', 'Cuota')
    Matricula = apps.get_model('modulo_pagos', 'Matricula')

    # Modelos antiguos (pueden o no existir según estado previo)
    try:
        PlanPagoColegiatura = apps.get_model('modulo_pagos', 'PlanPagoColegiatura')
    except LookupError:
        PlanPagoColegiatura = None
    try:
        PlanPagoPersonalizado = apps.get_model('modulo_pagos', 'PlanPagoPersonalizado')
    except LookupError:
        PlanPagoPersonalizado = None

    # Migrar PlanPagoColegiatura -> PlanPago
    if PlanPagoColegiatura is not None:
        for old in PlanPagoColegiatura.objects.all().iterator():
            plan, created = PlanPago.objects.get_or_create(
                estudiante_id=old.estudiante_id,
                evento_id=old.evento_id,
                defaults={
                    'numero_cuotas': old.numero_cuotas,
                    'monto_colegiatura': old.monto_total,
                    'usa_monto_personalizado': False,
                    'aplicar_beca_descuentos': True,
                    'activo': getattr(old, 'activo', True),
                }
            )

            # Reasignar cuotas manteniendo numeración original
            for cuota in Cuota.objects.filter(plan_pago_colegiatura_id=old.id).order_by('numero_cuota').iterator():
                cuota.plan_pago_id = plan.id
                # conservar numero_cuota; los conflictos se manejan al migrar personalizados
                cuota.save(update_fields=['plan_pago'])

            # Reasignar matrícula si corresponde
            Matricula.objects.filter(plan_pago_id=old.id).update(plan_pago_id=plan.id)

    # Migrar PlanPagoPersonalizado -> PlanPago (si no hay uno estándar ya)
    if PlanPagoPersonalizado is not None:
        for oldp in PlanPagoPersonalizado.objects.all().iterator():
            plan = PlanPago.objects.filter(estudiante_id=oldp.estudiante_id, evento_id=oldp.evento_id).first()
            if not plan:
                plan = PlanPago.objects.create(
                    estudiante_id=oldp.estudiante_id,
                    evento_id=oldp.evento_id,
                    numero_cuotas=oldp.numero_cuotas_personalizado,
                    monto_colegiatura=(oldp.monto_colegiatura_personalizado if oldp.monto_colegiatura_personalizado is not None else Decimal('0.00')),
                    usa_monto_personalizado=bool(oldp.monto_colegiatura_personalizado is not None),
                    aplicar_beca_descuentos=True,
                    activo=True,
                )

            # Anexar cuotas personalizadas al final para evitar conflictos de numeración
            existentes = Cuota.objects.filter(plan_pago_id=plan.id).values_list('numero_cuota', flat=True)
            max_num = max(list(existentes) + [0]) if existentes else 0
            for idx, cuota in enumerate(
                Cuota.objects.filter(plan_pago_personalizado_id=oldp.id)
                .order_by('numero_cuota')
                .iterator(),
                start=1,
            ):
                cuota.plan_pago_id = plan.id
                cuota.numero_cuota = max_num + idx
                # anular FK vieja para evitar unique_together temporal
                cuota.plan_pago_personalizado_id = None
                cuota.save(update_fields=['plan_pago', 'numero_cuota', 'plan_pago_personalizado'])


def migrate_planes_pago_backward(apps, schema_editor):
    # No se soporta revertir automáticamente esta migración de datos
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('modulo_certificados', '0001_initial'),
        ('modulo_estudiantes', '0001_initial'),
        ('modulo_pagos', '0010_pago_monto_aplicado_colegiatura_alter_pago_tipo_pago_and_more'),
    ]

    operations = [
        # Crear nuevo modelo PlanPago
        migrations.CreateModel(
            name='PlanPago',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_cuotas', models.PositiveIntegerField()),
                ('monto_colegiatura', models.DecimalField(decimal_places=2, max_digits=10)),
                ('usa_monto_personalizado', models.BooleanField(default=False)),
                ('aplicar_beca_descuentos', models.BooleanField(default=True)),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='planes_pago', to='modulo_estudiantes.estudiante')),
                ('evento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='planes_pago', to='modulo_certificados.evento')),
            ],
            options={
                'verbose_name': 'Plan de Pago',
                'verbose_name_plural': 'Planes de Pago',
                'unique_together': {('estudiante', 'evento')},
            },
        ),
        # Agregar M2M
        migrations.AddField(
            model_name='planpago',
            name='becas',
            field=models.ManyToManyField(blank=True, related_name='planes_pago', to='modulo_pagos.beca'),
        ),
        migrations.AddField(
            model_name='planpago',
            name='descuentos',
            field=models.ManyToManyField(blank=True, related_name='planes_pago', to='modulo_pagos.descuento'),
        ),
        # Agregar nueva FK a Cuota (temporalmente null)
        migrations.AddField(
            model_name='cuota',
            name='plan_pago',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='cuotas', to='modulo_pagos.planpago'),
        ),
        # Migrar datos
        migrations.RunPython(migrate_planes_pago_forward, migrate_planes_pago_backward),
        # Ajustar Matricula.plan_pago a nueva FK
        migrations.AlterField(
            model_name='matricula',
            name='plan_pago',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='matriculas', to='modulo_pagos.planpago'),
        ),
        # Asegurar unicidad en Cuota y remover FKs antiguas
        migrations.AlterUniqueTogether(
            name='cuota',
            unique_together={('plan_pago', 'numero_cuota')},
        ),
        migrations.RemoveField(
            model_name='cuota',
            name='plan_pago_colegiatura',
        ),
        migrations.RemoveField(
            model_name='cuota',
            name='plan_pago_personalizado',
        ),
        # Hacer no nula la FK nueva
        migrations.AlterField(
            model_name='cuota',
            name='plan_pago',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cuotas', to='modulo_pagos.planpago'),
        ),
        # Eliminar modelos antiguos
        migrations.DeleteModel(name='PlanPagoColegiatura'),
        migrations.DeleteModel(name='PlanPagoPersonalizado'),
    ]


