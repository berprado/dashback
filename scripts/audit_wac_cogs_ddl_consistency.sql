-- ========================================================================
-- SCRIPT DE AUDITORÍA: WAC, COGS, Márgenes
-- ========================================================================
-- Objetivo: Verificar consistencia de vistas y datos entre ambientes
-- Entornos: Ejecutar en AMBOS adminerp (producción) y adminerp_copy (pruebas)
-- Fecha: 2026-02-17
-- ========================================================================

-- IMPORTANTE: 
-- 1. Este script es SOLO LECTURA (SELECT sin modificaciones)
-- 2. No requiere privilegios de escritura
-- 3. Ejecutar en cada ambiente por separado
-- 4. Guardar resultados en archivo de texto para comparar

-- ========================================================================
-- PARTE 1: AUDITORÍA DE VISTAS EXISTENTES
-- ========================================================================

SELECT '=== PARTE 1: VISTAS EXISTENTES ===' AS seccion;

-- Listar todas las vistas WAC/COGS
SELECT 
    TABLE_NAME AS vista_nombre,
    TABLE_TYPE,
    TABLE_SCHEMA
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME LIKE 'vw_%'
  AND (
    TABLE_NAME LIKE '%wac%'
    OR TABLE_NAME LIKE '%cogs%'
    OR TABLE_NAME LIKE '%margen%'
    OR TABLE_NAME LIKE '%consumo%'
    OR TABLE_NAME LIKE '%costo%'
  )
ORDER BY TABLE_NAME;

-- ========================================================================
-- PARTE 2: AUDITORÍA DDL - VISTAS CRÍTICAS
-- ========================================================================

SELECT '=== PARTE 2: AUDITORÍA DDL ===' AS seccion;

-- Vista 1: vw_wac_producto_almacen (debe existir)
SELECT 
    'vw_wac_producto_almacen' AS vista,
    IF(
        (SELECT COUNT(*) FROM information_schema.TABLES 
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vw_wac_producto_almacen') > 0,
        'EXISTS',
        'MISSING'
    ) AS estado;

-- Vista 2: vw_wac_global_producto (debe existir?)
SELECT 
    'vw_wac_global_producto' AS vista,
    IF(
        (SELECT COUNT(*) FROM information_schema.TABLES 
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vw_wac_global_producto') > 0,
        'EXISTS',
        'MISSING'
    ) AS estado;

-- Vista 3: vw_cogs_comanda_combos (crítica)
SELECT 
    'vw_cogs_comanda_combos' AS vista,
    IF(
        (SELECT COUNT(*) FROM information_schema.TABLES 
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vw_cogs_comanda_combos') > 0,
        'EXISTS',
        'MISSING'
    ) AS estado;

-- Vista 4: vw_cogs_comanda (crítica)
SELECT 
    'vw_cogs_comanda' AS vista,
    IF(
        (SELECT COUNT(*) FROM information_schema.TABLES 
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vw_cogs_comanda') > 0,
        'EXISTS',
        'MISSING'
    ) AS estado;

-- Vista 5: vw_margen_comanda (crítica)
SELECT 
    'vw_margen_comanda' AS vista,
    IF(
        (SELECT COUNT(*) FROM information_schema.TABLES 
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vw_margen_comanda') > 0,
        'EXISTS',
        'MISSING'
    ) AS estado;

-- Vista 6: vw_consumo_valorizado_operativa (crítica)
SELECT 
    'vw_consumo_valorizado_operativa' AS vista,
    IF(
        (SELECT COUNT(*) FROM information_schema.TABLES 
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vw_consumo_valorizado_operativa') > 0,
        'EXISTS',
        'MISSING'
    ) AS estado;

-- ========================================================================
-- PARTE 3: COLUMNAS DE VISTAS CRÍTICAS
-- ========================================================================

SELECT '=== PARTE 3: COLUMNAS DE VISTAS ===' AS seccion;

-- Columnas de vw_margen_comanda
SELECT 
    'vw_margen_comanda' AS vista,
    COLUMN_NAME AS columna,
    COLUMN_TYPE AS tipo
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'vw_margen_comanda'
ORDER BY ORDINAL_POSITION;

-- Columnas de vw_cogs_comanda
SELECT 
    'vw_cogs_comanda' AS vista,
    COLUMN_NAME AS columna,
    COLUMN_TYPE AS tipo
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'vw_cogs_comanda'
ORDER BY ORDINAL_POSITION;

-- Columnas de vw_consumo_valorizado_operativa
SELECT 
    'vw_consumo_valorizado_operativa' AS vista,
    COLUMN_NAME AS columna,
    COLUMN_TYPE AS tipo
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME = 'vw_consumo_valorizado_operativa'
ORDER BY ORDINAL_POSITION;

-- ========================================================================
-- PARTE 4: VALIDACIÓN DE DATOS - OPERACIONALES ACTIVAS
-- ========================================================================

SELECT '=== PARTE 4: OPERACIONES ACTIVAS ===' AS seccion;

-- Obtener operaciones activas (para usar como referencia)
SELECT 
    id_operacion,
    estado,
    estado_operacion
FROM ope_operacion
WHERE estado = 'HAB'
  AND estado_operacion IN (22, 24)
LIMIT 1;

-- Si no hay operaciones activas, usar la más reciente cerrada
SELECT 
    id_operacion,
    estado,
    estado_operacion
FROM ope_operacion
WHERE estado = 'INA'
ORDER BY id_operacion DESC
LIMIT 1;

-- ========================================================================
-- PARTE 5: AUDITORÍA DE DATOS - VERIFICA CÁLCULOS
-- ========================================================================

SELECT '=== PARTE 5: CÁLCULO P&L (MARGEN) ===' AS seccion;

-- Para la PRIMERA operación activa (o la más reciente cerrada si no hay activas)
-- NOTA: Reemplaza 1130 con el id_operacion que obtengas de PARTE 4
-- Este es un TEMPLATE que debes adaptar con el id_operacion real

SELECT 
    'OPERACIÓN' AS contexto,
    1130 AS id_operacion_REEMPLAZAR_CON_ID_REAL,
    COUNT(DISTINCT id_comanda) AS total_comandas,
    COALESCE(SUM(total_venta), 0) AS total_ventas,
    COALESCE(SUM(cogs_comanda), 0) AS total_cogs,
    COALESCE(SUM(margen_comanda), 0) AS total_margen,
    ROUND(COALESCE(SUM(margen_comanda), 0) / NULLIF(COALESCE(SUM(total_venta), 0), 0) * 100, 2) AS margen_pct
FROM vw_margen_comanda
WHERE id_operacion = 1130;  -- CAMBIAR ESTE NÚMERO

-- ========================================================================
-- PARTE 6: AUDITORÍA DE DATOS - CONSUMO VALORIZADO
-- ========================================================================

SELECT '=== PARTE 6: CONSUMO VALORIZADO ===' AS seccion;

-- Para la MISMA operación (reemplaza 1130)
SELECT 
    'CONSUMO_TOTAL' AS contexto,
    COUNT(DISTINCT id_producto) AS productos_consumidos,
    SUM(cantidad_consumida_base) AS cantidad_total_base,
    COALESCE(SUM(costo_consumo), 0) AS costo_consumo_total
FROM vw_consumo_valorizado_operativa
WHERE id_operacion = 1130;  -- CAMBIAR ESTE NÚMERO

-- Top 5 productos por costo (para verificación manual)
SELECT 
    id_producto,
    cantidad_consumida_base,
    wac_operativa,
    costo_consumo
FROM vw_consumo_valorizado_operativa
WHERE id_operacion = 1130  -- CAMBIAR ESTE NÚMERO
ORDER BY costo_consumo DESC
LIMIT 5;

-- ========================================================================
-- PARTE 7: AUDITORÍA DE DATOS - COGS POR COMANDA
-- ========================================================================

SELECT '=== PARTE 7: COGS POR COMANDA ===' AS seccion;

-- Para la MISMA operación (reemplaza 1130)
-- Top 5 comandas por COGS (para verificación manual importante)
SELECT 
    id_comanda,
    cogs_comanda
FROM vw_cogs_comanda
WHERE id_operacion = 1130  -- CAMBIAR ESTE NÚMERO
ORDER BY cogs_comanda DESC
LIMIT 5;

-- Estadísticas de COGS por comanda
SELECT 
    'ESTADÍSTICAS_COGS' AS métrica,
    COUNT(DISTINCT id_comanda) AS comandas,
    ROUND(MIN(cogs_comanda), 2) AS cogs_min,
    ROUND(MAX(cogs_comanda), 2) AS cogs_max,
    ROUND(AVG(cogs_comanda), 2) AS cogs_promedio,
    ROUND(SUM(cogs_comanda), 2) AS cogs_total
FROM vw_cogs_comanda
WHERE id_operacion = 1130;  -- CAMBIAR ESTE NÚMERO

-- ========================================================================
-- PARTE 8: VERIFICACIÓN DE FUENTE DE WAC
-- ========================================================================

SELECT '=== PARTE 8: FUENTE DE WAC ===' AS seccion;

-- Muestra qué WAC se está usando realmente
-- Top 5 productos con su WAC
SELECT 
    id_producto,
    wac_operativa
FROM vw_consumo_valorizado_operativa
WHERE id_operacion = 1130  -- CAMBIAR ESTE NÚMERO
GROUP BY id_producto
LIMIT 5;

-- Si existe vw_wac_producto_almacen, compara
-- (ejecuta SOLO si la vista existe en este ambiente)
-- SELECT 
--     id_producto,
--     wac_global
-- FROM vw_wac_producto_almacen
-- GROUP BY id_producto
-- LIMIT 5;

-- ========================================================================
-- PARTE 9: AUDITORÍA FINAL - RESUMEN
-- ========================================================================

SELECT '=== PARTE 9: RESUMEN Y VALIDACIÓN ===' AS seccion;

-- Resumen de tablas base
SELECT 
    'bar_comanda' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT id_operacion) AS operaciones
FROM bar_comanda;

SELECT 
    'bar_detalle_comanda_salida' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT id_comanda) AS comandas
FROM bar_detalle_comanda_salida;

SELECT 
    'alm_ingreso' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT id_operacion) AS operaciones
FROM alm_ingreso;

SELECT 
    'alm_detalle_ingreso' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT id_producto) AS productos
FROM alm_detalle_ingreso;

-- ========================================================================
-- PARTE 10: VERIFICACIÓN ESPACIAL - INCONSISTENCIAS
-- ========================================================================

SELECT '=== PARTE 10: BUSCAR INCONSISTENCIAS ===' AS seccion;

-- Buscar comandas sin COGS (anomalía)
SELECT 
    'ANOMALÍA: Comandas sin COGS' AS tipo_anomalía,
    COUNT(*) AS cantidad
FROM bar_comanda bc
WHERE bc.id NOT IN (SELECT DISTINCT id_comanda FROM vw_cogs_comanda WHERE id_operacion = bc.id_operacion)
  AND bc.estado_comanda = 2;  -- Solo procesadas

-- Buscar comandas con COGS muy alto (>1000 Bs) - posible error
SELECT 
    'ANOMALÍA: COGS muy alto' AS tipo_anomalía,
    COUNT(*) AS cantidad
FROM vw_cogs_comanda
WHERE cogs_comanda > 1000;

-- ========================================================================
-- INSTRUCCIONES FINALES
-- ========================================================================

SELECT '
========================================================================
INSTRUCCIONES DE EJECUCIÓN Y ANÁLISIS
========================================================================

1. REEMPLAZAR id_operacion:
   - En PARTE 4, encuentra una operación activa (o usa la más reciente)
   - Reemplaza TODOS los "1130" en este script por ese id_operacion

2. EJECUTAR EN AMBOS AMBIENTES:
   - Primero en: adminerp_copy (localhost, pruebas)
   - Luego en:   adminerp (remoto vía tunel localtonet, producción)

3. GUARDAR RESULTADOS:
   - Guarda completo el output de cada ambiente
   - Nómbralos: audit_pruebas.txt, audit_produccion.txt
   - Compara línea por línea

4. VALIDAR COINCIDENCIA:
   - Si los números son IGUALES → ambientes consistentes ✅
   - Si son DIFERENTES → hay un problema que debe investigarse ❌

5. SI ENCUENTRAS DIFERENCIAS:
   - Documenta EXACTAMENTE qué es diferente
   - NO AVANCES con índices hasta resolver

========================================================================
' AS instrucciones;
