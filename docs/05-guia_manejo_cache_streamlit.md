---
name: streamlitcache
description: Habilidades y lineamientos para manejar persistencia, caching y optimización de rendimiento en dashboards con Streamlit. Cubre st.cache_data, st.cache_resource, session state, y patrones para conexiones a bases de datos. Usar cuando se trabaje con datos frecuentes, consultas a BD, o se necesite optimizar tiempos de carga.
---

# Streamlit Cache & Performance

Guía práctica para manejar caching, persistencia y rendimiento en aplicaciones Streamlit, especialmente dashboards con conexión a bases de datos.

> **Versión de referencia**: Streamlit 1.54.0 (Feb 4, 2026)
> **Compatibilidad**: 1.52.x → 1.54.x

---

## Conceptos Fundamentales

### El Modelo de Ejecución de Streamlit

Streamlit re-ejecuta el script completo en cada interacción. Sin caching:
- Cada click → re-consulta la BD
- Cada cambio de widget → re-procesa datos
- Múltiples usuarios → consultas duplicadas

El caching evita re-ejecuciones innecesarias almacenando resultados.

### Dos Decoradores, Dos Propósitos

| Decorador | Propósito | Serialización | Ejemplo |
|-----------|-----------|---------------|---------|
| `@st.cache_data` | Datos inmutables | Sí (pickle) | DataFrames, listas, dicts |
| `@st.cache_resource` | Recursos compartidos | No | Conexiones BD, modelos ML |

---

## st.cache_data — Para Datos

### Uso Básico

```python
import streamlit as st
import pandas as pd

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """Carga datos desde CSV. Cacheado automáticamente."""
    return pd.read_csv(path)

df = load_data("datos.csv")  # Solo lee archivo la primera vez
```

### TTL (Time To Live)

Controla cuánto tiempo permanece en cache:

```python
@st.cache_data(ttl=300)  # 5 minutos
def get_ventas_hoy() -> pd.DataFrame:
    """Datos que cambian frecuentemente."""
    return pd.read_sql("SELECT * FROM ventas WHERE fecha = CURDATE()", conn)

@st.cache_data(ttl=3600)  # 1 hora
def get_catalogo_productos() -> pd.DataFrame:
    """Datos que cambian poco."""
    return pd.read_sql("SELECT * FROM productos WHERE estado = 'HAB'", conn)

@st.cache_data(ttl=None)  # Sin expiración (default)
def get_configuracion() -> dict:
    """Datos estáticos."""
    return {"moneda": "Bs", "decimales": 2}
```

### 🆕 Scope de Sesión (Streamlit 1.53+)

Nuevo parámetro `scope` para aislar cache por usuario:

```python
# Cache global (default): compartido entre todos los usuarios
@st.cache_data
def get_precios_publicos() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM precios_publicos", conn)

# Cache por sesión: cada usuario tiene su propia copia
@st.cache_data(scope="session")
def get_carrito_usuario(user_id: str) -> list:
    """Datos específicos del usuario, no compartir entre sesiones."""
    return fetch_cart(user_id)

# Caso de uso: filtros personalizados por usuario
@st.cache_data(scope="session", ttl=60)
def get_datos_filtrados(op_ini: int, op_fin: int) -> pd.DataFrame:
    """Cache de consultas con filtros del usuario actual."""
    return pd.read_sql(f"""
        SELECT * FROM comandas 
        WHERE id_operacion BETWEEN {op_ini} AND {op_fin}
    """, conn)
```

**Cuándo usar `scope="session"`**:
- Datos personalizados por usuario
- Filtros/configuraciones de sesión
- Evitar que un usuario vea cache de otro
- Aplicaciones multi-tenant

### Invalidación Manual

```python
@st.cache_data
def get_ventas() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM ventas", conn)

# Botón para refrescar datos
if st.button("🔄 Actualizar"):
    st.cache_data.clear()  # Limpia TODO el cache de datos
    st.rerun()

# Invalidar función específica
get_ventas.clear()  # Solo limpia cache de get_ventas()
```

### Parámetros como Cache Key

Los argumentos de la función determinan la entrada del cache:

```python
@st.cache_data(ttl=300)
def get_ventas_operativa(op_id: int) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM ventas WHERE id_operacion = {op_id}", conn)

# Cada op_id diferente = entrada de cache diferente
df_1125 = get_ventas_operativa(1125)  # Cache miss → consulta BD
df_1125 = get_ventas_operativa(1125)  # Cache hit → retorna de memoria
df_1126 = get_ventas_operativa(1126)  # Cache miss → nueva consulta
```

---

## st.cache_resource — Para Recursos

### Conexiones a Base de Datos

```python
@st.cache_resource
def get_connection():
    """Conexión única compartida (pool manejado por el driver)."""
    return st.connection("mysql", type="sql")

conn = get_connection()  # Misma conexión en cada rerun
```

### 🆕 Cleanup con on_release (Streamlit 1.53+)

Ejecutar código cuando el recurso se libera:

```python
import logging

def cleanup_connection(conn):
    """Callback ejecutado al liberar la conexión."""
    logging.info("Cerrando conexión a BD...")
    try:
        conn.close()
    except Exception as e:
        logging.warning(f"Error al cerrar: {e}")

@st.cache_resource(on_release=cleanup_connection)
def get_db_connection():
    """Conexión con cleanup automático."""
    return create_engine("mysql://...")

# Scope por sesión + cleanup (ideal para conexiones por usuario)
@st.cache_resource(scope="session", on_release=cleanup_connection)
def get_user_connection(user_id: str):
    """Conexión aislada por usuario con limpieza al cerrar sesión."""
    return create_user_specific_connection(user_id)
```

**Casos de uso para `on_release`**:
- Cerrar conexiones de BD
- Liberar memoria de modelos ML
- Desuscribirse de streams/websockets
- Logging de auditoría

### Modelos ML y Recursos Pesados

```python
@st.cache_resource
def load_model():
    """Carga modelo una vez, comparte entre usuarios."""
    import joblib
    return joblib.load("modelo_prediccion.pkl")

model = load_model()
prediction = model.predict(input_data)
```

---

## Patrones para Dashboards con BD

### Patrón 1: Cache Diferenciado por Modo

Para dashboards con tiempo real e histórico:

```python
def fetch_dataframe(
    conn, 
    query: str, 
    params: dict | None = None,
    mode: str = "none",  # "none" | "ops" | "dates"
) -> pd.DataFrame:
    """
    Ejecuta query con TTL según modo operativo.
    
    - none (tiempo real): sin cache, datos frescos
    - ops/dates (histórico): cache 5 min, datos inmutables
    """
    ttl = 0 if mode == "none" else 300
    return conn.query(query, params=params or {}, ttl=ttl)
```

### Patrón 2: Cache en Capa de Servicio

Separar lógica de negocio del caching:

```python
# src/query_store.py — Sin caching (solo SQL)
def q_kpis(view_name: str, where_sql: str) -> str:
    return f"SELECT SUM(total) AS total FROM {view_name} {where_sql}"

# src/metrics.py — Con caching
@st.cache_data(ttl=300, show_spinner="Cargando KPIs...")
def get_kpis_cached(view_name: str, filters_hash: str) -> dict:
    """Wrapper cacheado para KPIs históricos."""
    conn = get_connection()
    # ... lógica de consulta ...
    return result

def get_kpis(conn, view_name: str, filters, mode: str) -> dict:
    """Punto de entrada: decide si cachear o no."""
    if mode in ("ops", "dates"):
        # Histórico: usar cache
        filters_hash = f"{filters.op_ini}_{filters.op_fin}"
        return get_kpis_cached(view_name, filters_hash)
    else:
        # Tiempo real: sin cache
        return _execute_kpis_query(conn, view_name, filters)
```

### Patrón 3: Prefetch en Background

Cargar datos anticipadamente:

```python
import concurrent.futures

@st.cache_data(ttl=300)
def prefetch_all_data(op_id: int) -> dict:
    """Carga múltiples consultas en paralelo."""
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            "kpis": executor.submit(get_kpis, op_id),
            "ventas_hora": executor.submit(get_ventas_hora, op_id),
            "top_productos": executor.submit(get_top_productos, op_id),
            "estado": executor.submit(get_estado_operativo, op_id),
        }
        
        results = {}
        for key, future in futures.items():
            try:
                results[key] = future.result(timeout=10)
            except Exception as e:
                results[key] = None
                st.warning(f"Error cargando {key}: {e}")
        
        return results

# En app.py
data = prefetch_all_data(operacion_id)
# Ahora todos los datos están en cache
```

### Patrón 4: Cache con Fallback

Degradación graceful cuando falla la BD:

```python
@st.cache_data(ttl=60)
def get_data_with_fallback(query: str) -> pd.DataFrame:
    """Intenta BD, fallback a cache previo."""
    try:
        return pd.read_sql(query, get_connection())
    except Exception as e:
        # Intentar recuperar del cache anterior
        cached = st.session_state.get(f"fallback_{hash(query)}")
        if cached is not None:
            st.warning("Mostrando datos en cache (BD no disponible)")
            return cached
        raise e

# Guardar en session_state como backup
df = get_data_with_fallback("SELECT * FROM ventas")
st.session_state[f"fallback_{hash(query)}"] = df
```

---

## 🆕 Mejoras de Widgets (1.53+)

### Identidad Basada en Key

Los widgets ya no resetean su valor al cambiar parámetros si tienen `key`:

```python
# Antes (1.52): Cambiar options reseteaba la selección
# Ahora (1.53+): Mantiene selección si key es igual

opciones_dinamicas = get_opciones_from_db()  # Puede cambiar

seleccion = st.multiselect(
    "Filtrar por categoría",
    options=opciones_dinamicas,
    key="filtro_categoria",  # 👈 Mantiene selección aunque options cambie
)

# También aplica a: st.selectbox, st.number_input, st.dataframe (con selecciones)
# Y en 1.54: st.area_chart, st.bar_chart, st.line_chart, st.scatter_chart
```

---

## 🆕 Mejoras en st.metric (1.53+)

### Formato de Números Configurado

```python
# Nuevo: parámetro de formato
st.metric(
    label="Total Vendido",
    value=1500000,
    format="%.2f",  # 1500000.00
)

# Con Markdown en value y delta
st.metric(
    label="Margen",
    value="**45.5%**",  # Markdown soportado
    delta="↑ 2.3%",
)
```

### Colores de Delta Personalizados

```python
st.metric(
    label="Temperatura",
    value="32°C",
    delta="+5°C",
    delta_color="red",  # Nuevo: paleta básica (red, green, blue, etc.)
)
```

---

## 🆕 Theming de Gráficos (1.54+)

### Colores Categóricos Configurables

```python
# En .streamlit/config.toml
# [theme]
# chartCategoricalColors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
# chartDivergingColors = ["#FF6B6B", "#FFFFFF", "#4ECDC4"]

# Los gráficos usan estos colores automáticamente
st.bar_chart(df, x="categoria", y="total", color="categoria")
```

---

## Session State para Persistencia de UI

### Estado entre Reruns

```python
# Inicializar estado
if "contador" not in st.session_state:
    st.session_state.contador = 0

if st.button("Incrementar"):
    st.session_state.contador += 1

st.write(f"Contador: {st.session_state.contador}")
```

### Patrón: Filtros Persistentes

```python
# Inicializar filtros con defaults
defaults = {
    "operativa_ini": 1125,
    "operativa_fin": 1125,
    "mostrar_detalle": False,
    "limite_top": 20,
}

for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Widgets vinculados a session_state
st.number_input(
    "Operativa inicio",
    key="operativa_ini",  # Se sincroniza automáticamente
)
```

---

## Optimización de Rendimiento

### 1. Fragmentos (@st.fragment) — Para Actualizaciones Parciales

```python
@st.fragment
def panel_actualizacion_rapida():
    """Este fragmento se puede refrescar sin re-ejecutar todo el script."""
    if st.button("Refrescar solo esto"):
        st.write(f"Actualizado: {datetime.now()}")

panel_actualizacion_rapida()
```

### 2. Lazy Loading con Expanders

```python
with st.expander("Ver detalle (carga bajo demanda)"):
    if st.checkbox("Cargar datos", key="load_detail"):
        # Solo consulta cuando el usuario lo pide
        detail_df = get_detalle_pesado()
        st.dataframe(detail_df)
```

### 3. Paginación para Datasets Grandes

```python
@st.cache_data(ttl=300)
def get_paginated_data(page: int, page_size: int = 100) -> pd.DataFrame:
    offset = page * page_size
    return pd.read_sql(f"""
        SELECT * FROM tabla 
        ORDER BY id DESC 
        LIMIT {page_size} OFFSET {offset}
    """, conn)

# UI de paginación
page = st.number_input("Página", min_value=0, value=0)
df = get_paginated_data(page)
st.dataframe(df)
```

### 4. Compresión de Cache

Para DataFrames muy grandes:

```python
import gzip
import pickle

@st.cache_data(ttl=3600)
def get_compressed_data() -> bytes:
    """Retorna datos comprimidos para reducir memoria."""
    df = pd.read_sql("SELECT * FROM tabla_enorme", conn)
    return gzip.compress(pickle.dumps(df))

def decompress_data(compressed: bytes) -> pd.DataFrame:
    return pickle.loads(gzip.decompress(compressed))

# Uso
compressed = get_compressed_data()
df = decompress_data(compressed)
```

---

## Debugging de Cache

### Verificar Estado del Cache

```python
# Ver estadísticas de cache
st.write("Cache stats:", st.cache_data)

# Spinner personalizado mientras carga
@st.cache_data(show_spinner="Consultando base de datos...")
def slow_query():
    return pd.read_sql("SELECT * FROM tabla_grande", conn)
```

### Forzar Recarga

```python
# En sidebar para admins
with st.sidebar:
    if st.button("🗑️ Limpiar cache completo"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
```

---

## Errores Comunes

### ❌ No usar objetos no-hashables como parámetros

```python
# MAL: DataFrame como parámetro
@st.cache_data
def process(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("categoria").sum()

# BIEN: pasar identificador hashable
@st.cache_data
def process(query_hash: str) -> pd.DataFrame:
    df = get_data(query_hash)
    return df.groupby("categoria").sum()
```

### ❌ No mutar datos cacheados

```python
# MAL: modifica el cache
@st.cache_data
def get_data() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3]})

df = get_data()
df["b"] = df["a"] * 2  # ⚠️ Modifica el objeto cacheado

# BIEN: trabajar con copia
df = get_data().copy()
df["b"] = df["a"] * 2
```

### ❌ No mezclar cache_data con recursos mutables

```python
# MAL: conexión en cache_data
@st.cache_data
def get_conn():
    return create_engine("...")  # Las conexiones son mutables

# BIEN: usar cache_resource
@st.cache_resource
def get_conn():
    return create_engine("...")
```

---

## Checklist de Rendimiento

| Aspecto | Verificar |
|---------|-----------|
| ✅ Cache TTL | ¿Datos históricos tienen TTL > 0? |
| ✅ Scope | ¿Datos personalizados usan `scope="session"`? |
| ✅ Lazy loading | ¿Datos pesados se cargan bajo demanda? |
| ✅ Cleanup | ¿Conexiones tienen `on_release`? |
| ✅ Fragmentos | ¿Secciones independientes usan `@st.fragment`? |
| ✅ Widgets | ¿Widgets dinámicos tienen `key` explícito? |

---

## Aplicación en Dashback (2026-02-11)

Implementado:
- TTL por modo en consultas (realtime sin cache, histórico con cache corto).
- Conexión cacheada por sesión con `on_release` y validación opcional.
- `@st.fragment` aplicado a secciones de KPIs, márgenes, gráficos y detalle.
- Fallback por sesión en gráficos (último DataFrame exitoso).

Pendiente / opcional:
- Theming de charts en `.streamlit/config.toml`.
- Fallback en KPIs/márgenes si se requiere degradación similar a gráficos.

---

## Referencias

- [Documentación oficial: Caching](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [API: st.cache_data](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)
- [API: st.cache_resource](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource)
- [Release Notes 1.53](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) — Session scope, on_release
- [Release Notes 1.54](https://docs.streamlit.io/develop/quick-reference/release-notes) — Chart theming, widget identity

---

*Última actualización: 2026-02-10*
*Compatible con: Streamlit 1.52.x → 1.54.x*
