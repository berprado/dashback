CREATE 
	DEFINER = 'root'@'localhost'
VIEW adminerp.vw_wac_global_producto
AS
	SELECT
	        `ch`.`id_producto`             AS `id_producto`,
	        `ch`.`costo_unitario_anterior` AS `wac_global`
	FROM
	        `vw_costo_heredado_producto` `ch`;

----

CREATE 
	DEFINER = 'root'@'localhost'
VIEW adminerp.vw_costo_heredado_producto
AS
	SELECT
	        `v`.`id_almacen`    AS `id_almacen`,
	        `v`.`id_producto`   AS `id_producto`,
	        `di`.`precio_costo` AS `costo_unitario_anterior`,
	        `i`.`id_operacion`  AS `id_operacion_costo`
	FROM
	        ((`vw_ultimo_ingreso_operacion` `v`
	    JOIN
	      `alm_ingreso` `i`
	        ON (((`i`.`id_operacion` = `v`.`id_operacion_ultima`)
	            AND (`i`.`id_almacen` = `v`.`id_almacen`))))
	    JOIN
	      `alm_detalle_ingreso` `di`
	        ON (((`di`.`id_ingreso` = `i`.`id`)
	            AND (`di`.`id_producto` = `v`.`id_producto`))))
	WHERE
	        (       (`i`.`estado` = 'HAB')
	                AND (`di`.`estado` = 'HAB')
	                AND (`di`.`precio_costo` > 0));
					
-----

CREATE 
	DEFINER = 'root'@'localhost'
VIEW adminerp.vw_ultimo_ingreso_operacion
AS
	SELECT
	        `i`.`id_almacen`        AS `id_almacen`,
	        `di`.`id_producto`      AS `id_producto`,
	        MAX(`i`.`id_operacion`) AS `id_operacion_ultima`
	FROM
	        (`alm_ingreso` `i`
	    JOIN
	      `alm_detalle_ingreso` `di`
	        ON ((`di`.`id_ingreso` = `i`.`id`)))
	WHERE
	        (       (`i`.`estado` = 'HAB')
	                AND (`di`.`estado` = 'HAB')
	                AND (`i`.`id_operacion` IS NOT NULL)
	                AND (`di`.`precio_costo` > 0))
	GROUP BY
	        `i`.`id_almacen`,
	        `di`.`id_producto`;

------

CREATE TABLE adminerp.alm_ingreso
  (
    id                 INT(11)      NOT NULL AUTO_INCREMENT,
    fecha              DATE         DEFAULT NULL,
    numero_documento   VARCHAR(255) DEFAULT NULL,
    observaciones      VARCHAR(255) DEFAULT NULL,
    recepcionado_por   VARCHAR(255) DEFAULT NULL,
    ind_estado_ingreso VARCHAR(1)   NOT NULL COMMENT '0: pendiente, 1: procesaro, 3: cancelado',
    ind_tipo_documento INT(11)      DEFAULT NULL,
    ind_tipo_pago      INT(11)      DEFAULT NULL,
    ind_tipo_ingreso   INT(11)      DEFAULT NULL,
    id_proveedor       INT(11)      DEFAULT NULL,
    id_almacen         INT(11)      NOT NULL,
    id_operacion       INT(11)      DEFAULT NULL,
    id_barra           INT(11)      DEFAULT NULL,
    usuario_reg        VARCHAR(255) NOT NULL,
    fecha_reg          DATE         DEFAULT NULL,
    fecha_mod          DATE         DEFAULT NULL,
    estado             VARCHAR(3)   NOT NULL,
    PRIMARY KEY (id)
  )
ENGINE = INNODB,
AUTO_INCREMENT = 1910,
AVG_ROW_LENGTH = 116,
CHARACTER SET latin1,
COLLATE latin1_swedish_ci;

ALTER TABLE adminerp.alm_ingreso
ADD INDEX fk_alm_ingreso_alm_almacen1_idx (id_almacen);

ALTER TABLE adminerp.alm_ingreso
ADD INDEX fk_alm_ingreso_alm_proveedor1_idx (id_proveedor);

ALTER TABLE adminerp.alm_ingreso
ADD CONSTRAINT alm_ingreso_ibfk_1 FOREIGN KEY (id_operacion)
REFERENCES adminerp.ope_operacion (id) ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE adminerp.alm_ingreso
ADD CONSTRAINT alm_ingreso_ibfk_2 FOREIGN KEY (id_barra)
REFERENCES adminerp.bar_barra (id) ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE adminerp.alm_ingreso
ADD CONSTRAINT fk_alm_ingreso_alm_almacen1 FOREIGN KEY (id_almacen)
REFERENCES adminerp.alm_almacen (id) ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE adminerp.alm_ingreso
ADD CONSTRAINT fk_alm_ingreso_alm_proveedor1 FOREIGN KEY (id_proveedor)
REFERENCES adminerp.alm_proveedor (id) ON DELETE NO ACTION ON UPDATE NO ACTION;

-----

CREATE TABLE adminerp.alm_detalle_ingreso
  (
    id                INT(11)        NOT NULL AUTO_INCREMENT,
    cantidad          DECIMAL(10, 2) NOT NULL,
    precio_costo      DECIMAL(10, 2) NOT NULL,
    precio_costo_real DECIMAL(10, 5) DEFAULT NULL,
    observaciones     VARCHAR(255)   DEFAULT NULL,
    ind_paq_detalle   VARCHAR(1)     DEFAULT NULL COMMENT '1: display 0:detalle',
    id_ingreso        INT(11)        NOT NULL,
    id_producto       INT(11)        NOT NULL,
    usuario_reg       VARCHAR(255)   NOT NULL,
    fecha_reg         DATE           DEFAULT NULL,
    fecha_mod         DATE           DEFAULT NULL,
    estado            VARCHAR(3)     NOT NULL,
    PRIMARY KEY (id)
  )
ENGINE = INNODB,
AUTO_INCREMENT = 6964,
AVG_ROW_LENGTH = 72,
CHARACTER SET latin1,
COLLATE latin1_swedish_ci;

ALTER TABLE adminerp.alm_detalle_ingreso
ADD INDEX fk_alm_detalle_ingreso_alm_ingreso1_idx (id_ingreso);

ALTER TABLE adminerp.alm_detalle_ingreso
ADD INDEX fk_alm_detalle_ingreso_alm_producto1_idx (id_producto);

ALTER TABLE adminerp.alm_detalle_ingreso
ADD CONSTRAINT fk_alm_detalle_ingreso_alm_ingreso1 FOREIGN KEY (id_ingreso)
REFERENCES adminerp.alm_ingreso (id) ON DELETE NO ACTION ON UPDATE NO ACTION;

ALTER TABLE adminerp.alm_detalle_ingreso
ADD CONSTRAINT fk_alm_detalle_ingreso_alm_producto1 FOREIGN KEY (id_producto)
REFERENCES adminerp.alm_producto (id) ON DELETE NO ACTION ON UPDATE NO ACTION;

----