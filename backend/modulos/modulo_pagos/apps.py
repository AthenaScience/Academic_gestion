from django.apps import AppConfig


class PagosConfig(AppConfig):
    name = 'modulos.modulo_pagos'
    verbose_name = 'Módulo de Pagos'

    def ready(self):  # noqa: D401
        # Registrar señales para crear plan/ cuotas automáticamente al matricular
        from . import signals  # noqa: F401
