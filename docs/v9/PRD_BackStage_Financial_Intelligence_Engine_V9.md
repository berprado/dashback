# 📘 PRD -- BackStage Financial Intelligence Engine V9

**Fecha de generación:** 22/02/2026 08:34:15 **Base de datos:**
adminerp\
**Versión MySQL:** 5.6.x

---

# 1. Visión del Producto

## Problema

La volatilidad económica generó distorsión en costos históricos y
pérdida de visibilidad real sobre márgenes.\
El sistema POS controlaba inventario correctamente, pero no entregaba
inteligencia financiera ejecutiva.

## Objetivo

Desarrollar un motor financiero capaz de:

- Calcular COGS en tiempo real
- Diferenciar margen real vs margen teórico
- Medir impacto financiero de cortesías
- Analizar rentabilidad por operativa, categoría y producto
- Servir como backend para dashboards ejecutivos

---

# 2. Alcance

## Incluido

- WAC dinámico basado en cache (`cache_wac_producto`)
- Trigger automático de actualización de WAC
- Vista base normalizada (`comandas_v8`)
- Motor financiero detallado (`comandas_v9_detallada`)
- KPIs consolidados
- Rankings gerenciales

## No incluido (roadmap futuro)

- Snapshot histórico de KPIs
- Alertas automáticas
- Simulación predictiva
- Integración BI externa

---

# 3. Arquitectura

## Capa 1 -- Datos Operativos

Tablas principales:

- bar_detalle_comanda_salida
- bar_comanda
- alm_producto
- bar_detalle_combo_bar
- cache_wac_producto

---

## Capa 2 -- Normalización de Consumo

Vista: `comandas_v8`

Funciones:

- Descompone combos
- Identifica tipo de parte (DIRECTO / PRINCIPAL / OPCIONAL)
- Calcula consumo en unidad base y unidad detalle

---

## Capa 3 -- Motor Financiero

Vista: `comandas_v9_detallada`

Agrega:

- WAC actual
- Costo total línea
- Venta real
- Venta teórica
- Margen real
- Margen teórico
- Pour cost real
- Pour cost teórico

---

## Capa 4 -- KPIs

- v9_kpi_operativa
- v9_kpi_operativa_categoria
- v9_kpi_operativa_tipo_parte

---

## Capa 5 -- Rankings

- v9_rank_producto_por_cogs
- v9_rank_producto_peor_pourcost
- v9_rank_item_vendido_margen_teorico

---

# 4. Definiciones Clave

## Venta Real

Monto efectivamente facturado.

## Venta Teórica

Monto original antes de cortesía.

## COGS

Costo real de insumos consumidos.

## Margen Real

Venta real - COGS

## Margen Teórico

Venta teórica - COGS

## Pour Cost

COGS / Venta

---

# 5. Flujos Operativos

## Flujo de Ingreso

1.  Registro en alm_detalle_ingreso
2.  Trigger actualiza cache_wac_producto
3.  WAC disponible inmediatamente

## Flujo de Venta

1.  Registro de comanda
2.  Descomposición de receta
3.  Aplicación de WAC
4.  Actualización automática de KPIs

---

# 6. Casos de Uso

### Gerencia

- Margen real por operativa
- Impacto financiero de cortesías
- Productos con peor rentabilidad
- Evaluación de política de precios

### Administración

- Auditoría de inventario valorizado
- Validación de coherencia financiera

---

# 7. Requerimientos No Funcionales

- Compatible MySQL 5.6
- Sin subqueries en FROM
- Bajo impacto en performance
- Basado en vistas simples

---

# 8. Métricas Disponibles

El sistema responde:

- ¿Cuál es el margen real de la operativa?
- ¿Cuánto costaron las cortesías?
- ¿Qué categoría es más rentable?
- ¿Qué producto tiene peor pour cost?
- ¿Qué combo es más rentable?

---

# 9. Riesgos y Mitigación

Riesgos:

- WAC mal inicializado
- Recetas incorrectas
- Ajustes manuales sin control

Mitigación:

- Cache controlado
- Trigger validado
- Consumo normalizado

---

# 10. Roadmap

## Fase 2

- Snapshot histórico por operativa

## Fase 3

- Dashboard Streamlit
- Alertas automáticas

## Fase 4

- Simulador de precios
- Simulación de variación de WAC

---

# Estado Actual

El motor V9 es:

- Matemáticamente consistente
- Audit-ready
- Escalable
- Dashboard-ready
- Adaptado a volatilidad económica

---

**Documento PRD generado automáticamente -- BackStage V9**
