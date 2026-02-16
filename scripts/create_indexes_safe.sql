-- ========================================================================
-- Script de creacion de indices minimos para MySQL 5.6.12 (modo seguro)
-- ========================================================================
-- Fecha: 2026-02-15
-- Entorno objetivo: adminerp_copy (pruebas) / adminerp (produccion)
-- Alcance: indices para optimizar vistas de WAC/COGS/margenes
-- Modo: verifica existencia antes de crear (evita duplicados)
-- ========================================================================

-- IMPORTANTE: MySQL 5.6.12 no soporta CREATE INDEX IF NOT EXISTS
-- Por eso, este script primero CONSULTA los indices existentes
-- y luego el DBA decide cuales ejecutar manualmente.

-- ========================================================================
-- PASO 1: Verificar indices existentes
-- ========================================================================

-- bar_comanda
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'bar_comanda'
GROUP BY TABLE_NAME, INDEX_NAME;

-- bar_detalle_comanda_salida
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'bar_detalle_comanda_salida'
GROUP BY TABLE_NAME, INDEX_NAME;

-- alm_detalle_ingreso
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'alm_detalle_ingreso'
GROUP BY TABLE_NAME, INDEX_NAME;

-- alm_ingreso
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'alm_ingreso'
GROUP BY TABLE_NAME, INDEX_NAME;

-- alm_producto
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'alm_producto'
GROUP BY TABLE_NAME, INDEX_NAME;

-- ope_operacion
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ope_operacion'
GROUP BY TABLE_NAME, INDEX_NAME;

-- parameter_table
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'parameter_table'
GROUP BY TABLE_NAME, INDEX_NAME;

-- ========================================================================
-- PASO 2: Crear indices faltantes (ejecutar solo los que NO existen)
-- ========================================================================

-- INSTRUCCIONES:
-- 1. Ejecuta las consultas del PASO 1 para ver indices existentes.
-- 2. Compara contra la lista de indices recomendados abajo.
-- 3. Ejecuta SOLO los que no existen (descomenta linea por linea).
-- 4. Valida con EXPLAIN antes/despues.

-- ========================================================================
-- bar_comanda
-- ========================================================================
-- NOTA IMPORTANTE: La columna en la tabla base es "fecha" (datetime).
-- Las vistas del dashboard (comandas_v6, etc.) la renombran como "fecha_emision".
-- Por lo tanto, este índice se crea sobre "fecha" pero se usa cuando se filtra
-- por "fecha_emision" en las vistas.

-- Recomendacion 1: (id_operacion, fecha)
-- Si ya existe fk_bar_comanda_ope_operacion1_idx solo en id_operacion,
-- este indice compuesto mejora filtros por operativa + rango de fechas.
-- ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_op_fecha (id_operacion, fecha);

-- Recomendacion 2: (estado, estado_comanda, estado_impresion)
-- Util para filtros de ventas finalizadas y diagnosticos de estado.
-- ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_estados (estado, estado_comanda, estado_impresion);

-- ========================================================================
-- bar_detalle_comanda_salida
-- ========================================================================
-- Recomendacion 3: (id_comanda, id_producto)
-- Mejora joins y agregaciones de detalle por comanda y producto.
-- Si ya existe indice simple en id_comanda, este lo reemplaza/complementa.
-- ALTER TABLE bar_detalle_comanda_salida ADD INDEX idx_detalle_comanda_producto (id_comanda, id_producto);

-- ========================================================================
-- alm_detalle_ingreso (opcional, solo si WAC es lento)
-- ========================================================================
-- NOTA: id_producto está aquí (no en alm_ingreso).
-- Recomendacion 4 (OPCIONAL): (id_ingreso, id_producto)
-- Solo necesario si vw_wac_producto_almacen tiene latencia alta.
-- Ya existen indices simples; este es para optimizar join + filtro.
-- ALTER TABLE alm_detalle_ingreso ADD INDEX idx_alm_detalle_ingreso_ing_producto (id_ingreso, id_producto);

-- ========================================================================
-- alm_ingreso
-- ========================================================================
-- NOTA IMPORTANTE: alm_ingreso NO tiene columna id_producto.
-- id_producto está en alm_detalle_ingreso (detalle de cada ingreso).
-- Recomendacion 5 (OPCIONAL): (fecha)
-- Solo si se filtra WAC por rango de fechas (no es el caso actual).
-- ALTER TABLE alm_ingreso ADD INDEX idx_alm_ingreso_fecha (fecha);

-- ========================================================================
-- alm_producto
-- ========================================================================
-- Recomendacion 6: (estado)
-- Util para filtros WHERE estado='HAB' en joins/vistas.
-- ALTER TABLE alm_producto ADD INDEX idx_alm_producto_estado (estado);

-- ========================================================================
-- ope_operacion
-- ========================================================================
-- Recomendacion 7: (estado, estado_operacion)
-- Mejora filtros de operativas activas y cerradas.
-- ALTER TABLE ope_operacion ADD INDEX idx_ope_operacion_estado (estado, estado_operacion);

-- ========================================================================
-- parameter_table
-- ========================================================================
-- Recomendacion 8: (id_master, estado)
-- Mejora joins de catalogo por id_master + filtro estado='HAB'.
-- ALTER TABLE parameter_table ADD INDEX idx_parameter_master_estado (id_master, estado);

-- ========================================================================
-- PASO 3: Validar mejoras con EXPLAIN
-- ========================================================================
-- Ejecutar las consultas del playbook (docs/playbook_performance_mysql56.md)
-- y comparar planes ANTES y DESPUES de crear indices.

-- Ejemplo rapido:
-- EXPLAIN SELECT SUM(total_venta), SUM(cogs_comanda), SUM(margen_comanda)
-- FROM vw_margen_comanda WHERE id_operacion = 1130;

-- Buscar mejoras en:
-- - type: de ALL a ref/range
-- - rows: reduccion significativa
-- - Using temporary / Using filesort: idealmente desaparece o se reduce

-- ========================================================================
-- FIN DEL SCRIPT
-- ========================================================================
