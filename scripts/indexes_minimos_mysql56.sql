-- Checklist de indices minimos para MySQL 5.6.12
-- Antes de ejecutar, validar nombres de tablas y columnas en tu esquema.
-- MySQL 5.6 no soporta IF NOT EXISTS para indices; verificar duplicados.

-- bar_comanda
ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_op_fecha (id_operacion, fecha_emision);
ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_estados (estado, estado_comanda, estado_impresion);
ALTER TABLE bar_comanda ADD INDEX idx_bar_comanda_id (id);

-- bar_detalle_comanda_salida
ALTER TABLE bar_detalle_comanda_salida ADD INDEX idx_detalle_comanda_producto (id_comanda, id_producto);
-- Solo si existe fecha_emision en detalle
-- ALTER TABLE bar_detalle_comanda_salida ADD INDEX idx_detalle_fecha (fecha_emision);

-- alm_ingreso
ALTER TABLE alm_ingreso ADD INDEX idx_alm_ingreso_producto (id_producto);
-- Solo si existe fecha_ingreso
-- ALTER TABLE alm_ingreso ADD INDEX idx_alm_ingreso_fecha (fecha_ingreso);

-- alm_producto
ALTER TABLE alm_producto ADD INDEX idx_alm_producto_estado (estado);

-- ope_operacion
ALTER TABLE ope_operacion ADD INDEX idx_ope_operacion_estado (estado, estado_operacion);

-- parameter_table
ALTER TABLE parameter_table ADD INDEX idx_parameter_master_estado (id_master, estado);

-- Fin de script
