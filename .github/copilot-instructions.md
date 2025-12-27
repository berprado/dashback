# Instrucciones Copilot — Dashback

## Contexto rápido
- App Streamlit (v1.52.2) en [app.py](../app.py) contra MySQL 5.6.12.
- Fuente de datos por vistas: `comandas_v6` (tiempo real) y `comandas_v6_todas`/`comandas_v6_base` (histórico).
- Arquitectura por capas en `src/` (no usar `config/`, `data/`, `components/`).

## Flujo principal (de extremo a extremo)
- UI → llama servicios en [src/metrics.py](../src/metrics.py) → generan SQL en [src/query_store.py](../src/query_store.py) → ejecutan con `fetch_dataframe` usando la conexión de [src/db.py](../src/db.py).
- El contexto inicial (tiempo real vs histórico) se decide en [src/startup.py](../src/startup.py) según `ope_operacion` (docs: [docs/01-flujo_inicio_dashboard.md](../docs/01-flujo_inicio_dashboard.md)).

## Conexión y entornos
- Config: `.streamlit/secrets.toml` (copiar desde `.streamlit/secrets.toml.example`).
- Conexiones soportadas: `connections.mysql` (Local) y opcional `connections.mysql_prod` (Producción); la UI solo muestra Producción si existe en `st.secrets`.
- No hardcodear esquema (`adminerp_copy.`/`adminerp.`): usar nombres no calificados y depender de la DB en la URL.
- Producción: credenciales **read-only**; la app está pensada para ejecutar solo `SELECT`.

## Convenciones que importan aquí
- Parametrización SQL: usar `:param` (SQLAlchemy/Streamlit Connections). Solo convertir a `%(param)s` en la ruta alternativa con `mysql.connector` (ya lo hace `fetch_dataframe`).
- Filtros: usar `Filters` + `build_where(filters, mode)`; `mode` es `none` (realtime), `ops` o `dates` (histórico).
- UX: en realtime el refresco es manual (botón “Actualizar”); puede existir operativa activa sin ventas (KPIs en 0 no es error).
- Streamlit: usar `width="stretch"` (evitar `use_container_width`).

## Formato Bolivia (moneda y números)
- Dinero: mostrar `Bs 1.100,33` (miles con punto, decimales con coma).
- Conteos: mostrar `1.100`.
- Centralización: reutilizar helpers en `src/ui/formatting.py`:
	- `format_bs`, `format_int`
	- `apply_plotly_bs` (ejes/hover Plotly)
	- `format_detalle_df` (tabla detalle)

Nota: en la tabla detalle, las columnas monetarias se formatean como texto para consistencia visual; si se ordena por esas columnas, el orden puede ser **lexicográfico**.

## KPIs/negocio (detalle crítico)
- Cortesías: el monto usa `cor_subtotal_anterior` cuando `tipo_salida='CORTESIA'` (porque `sub_total` puede ser 0).

## Estado operativo (reglas de negocio)
- Anuladas: `estado_comanda = 'ANULADO'`.
- Impresión:
	- `estado_impresion = 'PENDIENTE'` es temporal (en cola/por procesar).
	- `estado_impresion = 'IMPRESO'` ya fue procesado.
	- `estado_impresion IS NULL` suele indicar comanda anulada y es permanente.
- Por consistencia, el KPI/IDs de “no impresas” debe contar solo `estado_impresion='PENDIENTE'` (no incluir anuladas con NULL).

## Actividad (fecha_emision)
- El bloque “Actividad” calcula última comanda, minutos desde la última y ritmo (mediana entre comandas).
- SQL: `q_comandas_emision_times(...)` en `src/query_store.py` (1 fila por `id_comanda` con `MIN(fecha_emision)`).
- Servicio: `get_actividad_emision_comandas(..., recent_n=10)` en `src/metrics.py`.

## Workflows para dev/debug
- Ejecutar: `streamlit run app.py`.
- Ejecutar (auto-reload al guardar): `streamlit run app.py --server.runOnSave true`.
- Healthcheck UI: botón “Probar conexión” (usa `Q_HEALTHCHECK` y valida existencia de vistas).
- Debug de SQL: activar el checkbox “Mostrar SQL/params en errores” (renderiza `QueryExecutionError.sql` y `.params`).

## Dónde tocar para agregar una métrica
- SQL: agregar `q_...` en [src/query_store.py](../src/query_store.py).
- Servicio: agregar `get_...` en [src/metrics.py](../src/metrics.py) usando `_run_df` para envolver errores.
- UI: cablear en [app.py](../app.py) y renderizar en `st.metric`/Plotly (`src/ui/components.py`).

## Requisito: actualizar documentación tras cambios
Después de cualquier cambio funcional/UX, actualizar como mínimo:
- `README.md` (qué cambió para el usuario)
- `docs/03-evolucion_y_mejoras.md` (registro de evolución)
- `docs/02-guia_dashboard_backstage.md` (si cambia arquitectura, reglas, o semántica)

Si el cambio afecta el arranque (realtime/histórico) o casos límite, actualizar también `docs/01-flujo_inicio_dashboard.md`.

## Checklist de cierre (antes de dar por listo)
- Compila en el entorno virtual: `C:/.../.venv/Scripts/python.exe -m py_compile ...`.
- Verifica formato Bolivia en UI (métricas, gráficos y detalle): `Bs 1.100,33` y conteos `1.100`.
- Verifica semántica de impresión/anulación: “no impresas” = `estado_impresion='PENDIENTE'` (no incluye `NULL`).
- Si tocaste SQL/servicios/UI: revisa consistencia end-to-end (query_store → metrics → app/ui).
- Actualiza documentación (README + docs/03 + docs/02; y docs/01 si aplica) y deja explícitos trade-offs relevantes (p.ej. orden lexicográfico en detalle).
