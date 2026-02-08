Detengamos nuestro avance, una parada operativa. Mientras acampamos vamos a revisar nuestro arsenal.

Te adjunto las consulñtas que estoy utilizando. 
Si tenemos una operativa abierta deberiamos usar ese numero de operativa, en este caso estoy usando la 1125 como referencia.
Si no tenemos operativa abierta deberiamos permitir al usuario selecco


----
Consulta de resumen económico de la operativa:

¿Qué hace?

Entrega el P&L consolidado de la operativa (solo ventas reales, sin cortesías):

ventas
Suma todo lo facturado en la operativa (comandas VENTA).

cogs
Suma el costo total de los insumos consumidos (combos + comandables si ya están integrados).

margen
Utilidad bruta total = ventas − cogs.

¿Para qué sirve?

Validación contra ope_conciliacion.

Base directa para:

dashboard financiero

margen por día / operativa

control de rentabilidad global

👉 Esta es la consulta ejecutiva. La que mira el dueño.



SELECT
    SUM(total_venta)     AS ventas,
    SUM(cogs_comanda)    AS cogs,
    SUM(margen_comanda)  AS margen
FROM vw_margen_comanda
WHERE id_operacion = 1125;

----

-----
Consulta de detalle por comanda

¿Qué hace?

Devuelve una fila por comanda, con:

total_venta

cogs_comanda

margen_comanda

¿Para qué sirve?

Auditoría fina:

detectar comandas con margen anómalo

detectar errores de receta / WAC

Análisis operativo:

¿qué tipo de comandas generan mejor margen?

¿qué bartender / turno vende mejor?

👉 Esta es la consulta táctica. La que mira el jefe de barra.


SELECT *
FROM vw_margen_comanda
WHERE id_operacion = 1125;

-----
-----

Consulta de consumo valorizado de insumos

¿Qué hace?

Muestra qué insumos se consumieron realmente, agregados por producto:

cantidad_consumida_base (en unidades base)

wac_operativa / wac_global

costo_consumo total por producto

¿Para qué sirve?

Conciliar contra inventario físico.

Detectar:

mermas

recetas mal definidas

errores de multiplicación de cantidades

Base para:

análisis de costos por producto

renegociación con proveedores

👉 Esta es la consulta logística. La que mira inventarios y control.

SELECT *
FROM vw_consumo_valorizado_operativa
WHERE id_operacion = 1125;

-----

-----

Consumo sin valorar (sanidad de cantidades)

¿Por qué es clave?

Aísla el problema de cantidades del problema de costos.

Si algo está mal aquí:

no es WAC

no es margen

es receta / multiplicación / unidades

👉 Regla de oro:

Si el consumo está mal, todo lo demás estará mal aunque el WAC sea perfecto.

SELECT *
FROM vw_consumo_insumos_operativa
WHERE id_operacion = 1125;
-----

-----

COGS por comanda (sin ventas)

¿Para qué sirve?

Ver solo el costo, sin precio de venta.

Ideal para:

cortesías (que no tienen venta pero sí COGS)

auditoría de consumo puro

👉 Esta consulta es la bisagra entre inventario y finanzas.

SELECT *
FROM vw_cogs_comanda
WHERE id_operacion = 1125;

----
----
Mapa mental:

Recetas + Cantidades vendidas
        ↓
vw_combo_detalle_operacion
        ↓
vw_consumo_insumos_operativa   ← (sanidad de cantidades)
        ↓
vw_consumo_valorizado_operativa ← (costo por producto)
        ↓
vw_cogs_comanda
        ↓
vw_margen_comanda
        ↓
Resumen ejecutivo (ventas / cogs / margen)

-----


