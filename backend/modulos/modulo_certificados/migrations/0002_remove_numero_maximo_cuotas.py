from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modulo_certificados', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='evento',
            name='numero_maximo_cuotas',
        ),
    ]


