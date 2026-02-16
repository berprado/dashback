-- Checklist de indices minimos para MySQL 5.6.12 (validado contra adminerp_copy)
-- Antes de ejecutar, validar nombres de tablas y columnas en tu esquema.
-- MySQL 5.6 no soporta IF NOT EXISTS para indices; verificar duplicados.

-- Sugerencia: verifica existencia del indice antes de crear
-- SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS cols
-- FROM information_schema.STATISTICS
-- WHERE TABLE_SCHEMA = 'adminerp_copy' AND TABLE_NAME = 'bar_comanda'
-- GROUP BY INDEX_NAME;

-- bar_comanda
ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_op_fecha (id_operacion, fecha);
ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_estados (estado, estado_comanda, estado_impresion);

-- bar_detalle_comanda_salida
ALTER TABLE bar_detalle_comanda_salida ADD INDEX idx_detalle_comanda_producto (id_comanda, id_producto);

-- alm_detalle_ingreso (clave para WAC)
-- Ya existen indices simples por id_ingreso y id_producto.
-- Opcional si hay latencia en WAC: indice compuesto para join + filtro.
-- ALTER TABLE alm_detalle_ingreso ADD INDEX idx_alm_detalle_ingreso_ing_producto (id_ingreso, id_producto);

-- alm_ingreso
-- No tiene id_producto; no aplicar indice aqui.
-- Opcional si se filtra por fecha: ALTER TABLE alm_ingreso ADD INDEX idx_alm_ingreso_fecha (fecha);

-- alm_producto
ALTER TABLE alm_producto ADD INDEX idx_alm_producto_estado (estado);

-- ope_operacion
ALTER TABLE ope_operacion ADD INDEX idx_ope_operacion_estado (estado, estado_operacion);

-- parameter_table
ALTER TABLE parameter_table ADD INDEX idx_parameter_master_estado (id_master, estado);

-- Fin de script
