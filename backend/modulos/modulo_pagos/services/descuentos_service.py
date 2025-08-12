from decimal import Decimal
from django.utils import timezone
from ..models import Beca, Descuento

class DescuentosService:
    """
    Servicio para calcular y aplicar descuentos y becas automáticamente.
    """
    
    @staticmethod
    def calcular_descuento_total(estudiante_id, evento_id, tipo_pago, monto_original):
        """
        Calcula el descuento total aplicable combinando becas y descuentos.
        
        Args:
            estudiante_id: ID del estudiante
            evento_id: ID del evento
            tipo_pago: Tipo de pago ('matricula', 'colegiatura', 'certificado')
            monto_original: Monto original sin descuentos
            
        Returns:
            dict: Información del descuento calculado
        """
        hoy = timezone.now().date()
        
        # Obtener becas activas
        becas = Beca.objects.filter(
            estudiante_id=estudiante_id,
            evento_id=evento_id,
            estado='activa',
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        # Obtener descuentos activos
        descuentos = Descuento.objects.filter(
            estudiante_id=estudiante_id,
            evento_id=evento_id,
            estado='activo',
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        descuento_total = Decimal('0.00')
        becas_aplicadas = []
        descuentos_aplicados = []
        
        # Calcular descuentos de becas
        for beca in becas:
            descuento = beca.calcular_descuento(monto_original, tipo_pago)
            if descuento > 0:
                descuento_total += descuento
                becas_aplicadas.append({
                    'id': beca.id,
                    'nombre': beca.nombre_beca,
                    'tipo': beca.tipo_beca,
                    'descuento': descuento,
                    'porcentaje': beca.porcentaje_descuento,
                    'monto_fijo': beca.monto_descuento
                })
        
        # Calcular descuentos promocionales
        for descuento in descuentos:
            descuento_valor = descuento.calcular_descuento(monto_original, tipo_pago)
            if descuento_valor > 0:
                descuento_total += descuento_valor
                descuentos_aplicados.append({
                    'id': descuento.id,
                    'nombre': descuento.nombre_descuento,
                    'tipo': descuento.tipo_descuento,
                    'descuento': descuento_valor,
                    'porcentaje': descuento.porcentaje_descuento,
                    'monto_fijo': descuento.monto_descuento,
                    'codigo_promocional': descuento.codigo_promocional
                })
        
        # Calcular monto final
        monto_final = monto_original - descuento_total
        
        return {
            'monto_original': monto_original,
            'descuento_total': descuento_total,
            'monto_final': monto_final,
            'becas_aplicadas': becas_aplicadas,
            'descuentos_aplicados': descuentos_aplicados,
            'resumen': {
                'total_becas': len(becas_aplicadas),
                'total_descuentos': len(descuentos_aplicados),
                'porcentaje_descuento_total': (descuento_total / monto_original * 100) if monto_original > 0 else 0
            }
        }
    
    @staticmethod
    def obtener_resumen_beneficios(estudiante_id, evento_id):
        """
        Obtiene un resumen de todos los beneficios (becas y descuentos) de un estudiante en un evento.
        
        Args:
            estudiante_id: ID del estudiante
            evento_id: ID del evento
            
        Returns:
            dict: Resumen de beneficios
        """
        hoy = timezone.now().date()
        
        # Obtener becas activas
        becas = Beca.objects.filter(
            estudiante_id=estudiante_id,
            evento_id=evento_id,
            estado='activa',
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        # Obtener descuentos activos
        descuentos = Descuento.objects.filter(
            estudiante_id=estudiante_id,
            evento_id=evento_id,
            estado='activo',
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        resumen = {
            'estudiante_id': estudiante_id,
            'evento_id': evento_id,
            'fecha_consulta': hoy,
            'becas_activas': [],
            'descuentos_activos': [],
            'total_beneficios': 0
        }
        
        # Procesar becas
        for beca in becas:
            resumen['becas_activas'].append({
                'id': beca.id,
                'nombre': beca.nombre_beca,
                'tipo': beca.tipo_beca,
                'porcentaje': beca.porcentaje_descuento,
                'monto_fijo': beca.monto_descuento,
                'aplica_a': {
                    'matricula': beca.aplica_matricula,
                    'colegiatura': beca.aplica_colegiatura,
                    'certificado': beca.aplica_certificado
                },
                'vigencia': {
                    'inicio': beca.fecha_inicio,
                    'fin': beca.fecha_fin
                }
            })
            resumen['total_beneficios'] += 1
        
        # Procesar descuentos
        for descuento in descuentos:
            resumen['descuentos_activos'].append({
                'id': descuento.id,
                'nombre': descuento.nombre_descuento,
                'tipo': descuento.tipo_descuento,
                'porcentaje': descuento.porcentaje_descuento,
                'monto_fijo': descuento.monto_descuento,
                'aplica_a': {
                    'matricula': descuento.aplica_matricula,
                    'colegiatura': descuento.aplica_colegiatura,
                    'certificado': descuento.aplica_certificado
                },
                'vigencia': {
                    'inicio': descuento.fecha_inicio,
                    'fin': descuento.fecha_fin
                },
                'codigo_promocional': descuento.codigo_promocional
            })
            resumen['total_beneficios'] += 1
        
        return resumen
    
    @staticmethod
    def validar_codigo_promocional(codigo, estudiante_id, evento_id):
        """
        Valida si un código promocional es válido para un estudiante y evento específicos.
        
        Args:
            codigo: Código promocional
            estudiante_id: ID del estudiante
            evento_id: ID del evento
            
        Returns:
            dict: Información del descuento si es válido, None si no
        """
        hoy = timezone.now().date()
        
        try:
            descuento = Descuento.objects.get(
                codigo_promocional=codigo,
                estado='activo',
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy
            )
            
            # Verificar si aplica al estudiante y evento
            if descuento.estudiante_id == estudiante_id and descuento.evento_id == evento_id:
                return {
                    'valido': True,
                    'descuento': {
                        'id': descuento.id,
                        'nombre': descuento.nombre_descuento,
                        'tipo': descuento.tipo_descuento,
                        'porcentaje': descuento.porcentaje_descuento,
                        'monto_fijo': descuento.monto_descuento,
                        'aplica_a': {
                            'matricula': descuento.aplica_matricula,
                            'colegiatura': descuento.aplica_colegiatura,
                            'certificado': descuento.aplica_certificado
                        }
                    }
                }
            else:
                return {
                    'valido': False,
                    'error': 'El código promocional no aplica para este estudiante o evento'
                }
                
        except Descuento.DoesNotExist:
            return {
                'valido': False,
                'error': 'Código promocional no válido o expirado'
            }
