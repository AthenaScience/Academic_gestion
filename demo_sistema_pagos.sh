#!/bin/bash

# Script de Demostración del Sistema de Pagos por Cuotas
# Sistema de Gestión Académica

echo "🎓 DEMOSTRACIÓN DEL SISTEMA DE PAGOS POR CUOTAS"
echo "================================================"
echo ""

# Colores para la salida
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar títulos
show_title() {
    echo -e "${BLUE}$1${NC}"
    echo "----------------------------------------"
}

# Función para mostrar comandos
show_command() {
    echo -e "${YELLOW}Comando:${NC} $1"
    echo -e "${GREEN}Descripción:${NC} $2"
    echo ""
}

# Función para mostrar ejemplo
show_example() {
    echo -e "${YELLOW}Ejemplo:${NC}"
    echo "  $1"
    echo ""
}

echo "Este script demuestra cómo usar el Sistema de Pagos por Cuotas completo."
echo ""

# 1. Comando para crear plan de pago
show_title "1. CREAR PLAN DE PAGO PARA UN ESTUDIANTE"
show_command "./start_dev.sh django crear_plan_pago --estudiante_id 1 --evento_id 1" \
    "Crea un plan de pago completo para un estudiante en un evento específico"
show_example "./start_dev.sh django crear_plan_pago --estudiante_id 1 --evento_id 1 --numero_cuotas 6"

echo "Este comando:"
echo "  • Crea un plan de pago para el estudiante"
echo "  • Genera automáticamente las cuotas mensuales"
echo "  • Crea la matrícula del estudiante"
echo "  • Inicializa el estado de pagos"
echo ""

# 2. Comando para registrar pagos
show_title "2. REGISTRAR PAGO DE CUOTA"
show_command "./start_dev.sh django registrar_pago_cuota --cuota_id 1 --monto_pagado 100.00 --metodo_pago transferencia" \
    "Registra el pago de una cuota específica"
show_example "./start_dev.sh django registrar_pago_cuota --cuota_id 1 --monto_pagado 100.00 --metodo_pago transferencia --institucion_financiera_id 1 --codigo_comprobante 'TRX-001'"

echo "Este comando:"
echo "  • Registra el pago de la cuota"
echo "  • Actualiza el estado de la cuota"
echo "  • Actualiza el estado general del estudiante"
echo "  • Permite adjuntar comprobantes y observaciones"
echo ""

# 3. Comando para verificar cuotas atrasadas
show_title "3. VERIFICAR CUOTAS ATRASADAS"
show_command "./start_dev.sh django verificar_cuotas_atrasadas" \
    "Verifica y marca las cuotas que están atrasadas"
show_example "./start_dev.sh django verificar_cuotas_atrasadas --mostrar_estudiantes"

echo "Este comando:"
echo "  • Busca cuotas vencidas y las marca como atrasadas"
echo "  • Actualiza el estado de pagos del evento"
echo "  • Puede mostrar lista de estudiantes atrasados"
echo ""

# 4. Comando para resumen de estudiante
show_title "4. RESUMEN COMPLETO DE ESTUDIANTE"
show_command "./start_dev.sh django resumen_estudiante --estudiante_id 1 --evento_id 1" \
    "Muestra el resumen completo del estado de pagos de un estudiante"
show_example "./start_dev.sh django resumen_estudiante --estudiante_id 1 --evento_id 1"

echo "Este comando muestra:"
echo "  • Estado de matrícula, colegiatura y certificado"
echo "  • Progreso de pagos en porcentaje"
echo "  • Detalle de cada cuota"
echo "  • Recomendaciones basadas en el estado"
echo ""

# 5. Comando para estadísticas de evento
show_title "5. ESTADÍSTICAS COMPLETAS DEL EVENTO"
show_command "./start_dev.sh django estadisticas_evento --evento_id 1" \
    "Muestra estadísticas completas de pagos para un evento"
show_example "./start_dev.sh django estadisticas_evento --evento_id 1 --mostrar_estudiantes_atrasados"

echo "Este comando muestra:"
echo "  • Estadísticas generales del evento"
echo "  • Total de estudiantes y cuotas"
echo "  • Progreso general de pagos"
echo "  • Lista de estudiantes atrasados"
echo "  • Análisis y recomendaciones"
echo ""

# Flujo de trabajo completo
show_title "FLUJO DE TRABAJO COMPLETO"
echo "1. 📚 Configurar evento con costos (matrícula, colegiatura, certificado)"
echo "2. 👤 Matricular estudiante usando 'crear_plan_pago'"
echo "3. 💰 Registrar pagos mensuales usando 'registrar_pago_cuota'"
echo "4. 🔍 Monitorear estado usando 'resumen_estudiante'"
echo "5. ⚠️  Verificar cuotas atrasadas usando 'verificar_cuotas_atrasadas'"
echo "6. 📊 Revisar estadísticas del evento usando 'estadisticas_evento'"
echo ""

# Casos de uso
show_title "CASOS DE USO COMUNES"
echo "🆕 Nuevo Estudiante:"
echo "   ./start_dev.sh django crear_plan_pago --estudiante_id 1 --evento_id 1"
echo ""
echo "💳 Pago Mensual:"
echo "   ./start_dev.sh django registrar_pago_cuota --cuota_id 1 --monto_pagado 100.00 --metodo_pago transferencia"
echo ""
echo "📊 Monitoreo Diario:"
echo "   ./start_dev.sh django verificar_cuotas_atrasadas --mostrar_estudiantes"
echo "   ./start_dev.sh django estadisticas_evento --evento_id 1"
echo ""

# Verificación del sistema
show_title "VERIFICACIÓN DEL SISTEMA"
echo "Para verificar que todo esté funcionando:"
echo "  ./start_dev.sh django check"
echo "  ./start_dev.sh django showmigrations"
echo ""

echo -e "${GREEN}¡El Sistema de Pagos por Cuotas está listo para usar! 🎉${NC}"
echo ""
echo "📖 Para más información, consulta la documentación en: docs/SISTEMA_PAGOS_CUOTAS.md"
echo ""
echo "🚀 ¡Comienza a usar el sistema!"
