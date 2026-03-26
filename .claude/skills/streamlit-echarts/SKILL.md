---
name: streamlit-echarts
description: >
  Dominio completo de streamlit-echarts: crear, configurar y conectar gráficos ECharts
  dentro de apps Streamlit. Aplica cuando el usuario pide construir dashboards, charts,
  visualizaciones interactivas, KPIs, drilldowns o cualquier gráfico con st_echarts o
  st_pyecharts. Cubre API completa (parámetros, eventos, on_select), patrones avanzados
  (drilldown con universalTransition, @st.fragment, replace_merge), JsCode/gradientes,
  theming adaptativo y arquitectura de showcase dashboards con filtros y cross-chart
  interaction.
---

# streamlit-echarts — Skill Completo

`streamlit-echarts` es un componente Streamlit que renderiza gráficos Apache ECharts
usando un dict Python como `options`. Admite también PyECharts vía `st_pyecharts`.

## 1. Instalación y requisitos

```bash
# Versión mínima requerida
pip install "streamlit>=1.53" "streamlit-echarts[pyecharts]>=0.6.0"
```

Requerimientos: Python ≥ 3.10, Streamlit ≥ 1.53.

---

## 2. Parámetros de `st_echarts`

```python
from streamlit_echarts import st_echarts

result = st_echarts(
    options,                  # dict  — REQUERIDO. ECharts option object.
    *,
    theme=...,                # str | dict — ver sección 7
    events=...,               # dict[str, str_js] — ver sección 5
    on_select=...,            # "rerun" | callable — ver sección 5
    selection_mode=...,       # "points" | ("box","lasso") — ver sección 5
    on_change=...,            # callable Python — se ejecuta server-side al disparar evento
    height="300px",           # str CSS
    width="100%",             # str CSS
    renderer="canvas",        # "canvas" | "svg"
    replace_merge=None,       # str | list[str] — ver sección 6
    key=None,                 # str — SIEMPRE usar para charts con estado
    map=None,                 # objeto Map para GeoJSON personalizado
)
```

### Valor de retorno

`result` es un objeto con:
- `result["selection"]["point_indices"]` — índices de puntos seleccionados (con `on_select`)
- `result["selection"]["points"]` — lista de puntos `{name, value, ...}`
- `result.chart_event` — valor retornado por el handler JS en `events`

---

## 3. Conversión JS → Python (reglas fundamentales)

| JavaScript | Python |
|---|---|
| `{ key: value }` | `{"key": value}` — SIEMPRE comillas en claves |
| `true` / `false` | `True` / `False` |
| `null` | `None` |
| Comillas simples `'str'` | Comillas dobles `"str"` |
| `[{...}, {...}]` | lista de dicts |
| `series: {...}` (objeto único) | `"series": {...}` dict |
| `series: [{...}]` (array) | `"series": [{...}]` lista |

**Regla crítica:** preservar la forma original de `series` (dict vs lista).

---

## 4. JsCode — funciones y gradientes

Importar: `from streamlit_echarts import JsCode`

Usar **solo** cuando ECharts espera una función JS o constructor JS (`new ...`).
NO usar para strings estáticos, números ni formateadores sin lógica.

### Formatters

```python
# tooltip.formatter
"formatter": JsCode("function(params) { return params.name + ': ' + params.value; }").js_code

# axisLabel.formatter
"formatter": JsCode("function(value) { return '$' + value.toLocaleString(); }").js_code

# valueFormatter en series
"valueFormatter": JsCode("function(value) { return value + ' ml'; }").js_code

# Formatter con múltiples series
"formatter": JsCode("""
    function(params) {
        var s = params[0].name + '<br/>';
        params.forEach(function(p) {
            s += p.marker + p.seriesName + ': ' + p.value + '<br/>';
        });
        return s;
    }
""").js_code
```

### Gradientes lineales

```python
"color": JsCode(
    "new echarts.graphic.LinearGradient(0, 0, 0, 1, ["
    "{offset: 0, color: 'rgb(128, 255, 165)'},"
    "{offset: 1, color: 'rgb(1, 191, 236)'}"
    "])"
).js_code
```

Dirección del gradiente: `(x0, y0, x1, y1)` — `(0,0,0,1)` es vertical top→bottom.

### symbolSize dinámico

```python
"symbolSize": JsCode("function(v) { return v[2] * 5; }").js_code
```

### Posición dinámica de tooltip

```python
"position": JsCode("""
    function(pos, params, el, elRect, size) {
        var obj = {top: 60};
        obj[['left','right'][+(pos[0] < size.viewSize[0] / 2)]] = 5;
        return obj;
    }
""").js_code
```

---

## 5. Interactividad — eventos y selección

### `on_select` (recomendado para clicks y brush)

```python
# Click simple — devuelve índices
result = st_echarts(
    options=options,
    on_select="rerun",
    selection_mode="points",
    key="my_chart",
)
indices = result["selection"]["point_indices"]
points  = result["selection"]["points"]  # [{name, value, ...}, ...]

# Brush (lasso/box) — activar toolbar primero
result = st_echarts(
    options=options,
    on_select="rerun",
    selection_mode=("box", "lasso"),
    key="brush_chart",
)
```

### `events` (bajo nivel — para mouseover, legendselectchanged, valores custom)

```python
result = st_echarts(
    options=options,
    events={
        "click": "function(params) { return {name: params.name, value: params.value} }",
        "mouseover": "function(params) { return params.name }",
        "legendselectchanged": "function(params) { return params.selected }",
        "dblclick": "function(params) { return [params.type, params.name, params.value] }",
    },
    key="events_chart",
)
if result and result.chart_event:
    st.write(result.chart_event)
```

El valor **retornado por la función JS** es lo que aparece en `result.chart_event`.

### `on_change` (callback Python server-side)

```python
def handle_change():
    st.session_state.clicks += 1

st_echarts(
    options=options,
    events={"click": "function(p){ return p.name }"},
    on_change=handle_change,
    key="cb_chart",
)
```

---

## 6. Drilldown con `universalTransition` y `replace_merge`

Patrón completo para animación morph entre vistas (top-level → detalle):

```python
import streamlit as st
from streamlit_echarts import st_echarts

DRILLDOWN_DATA = {
    "animals": [["Cats", 4], ["Dogs", 2], ["Cows", 1], ["Sheep", 2], ["Pigs", 1]],
    "fruits":  [["Apples", 4], ["Oranges", 2]],
    "cars":    [["Toyota", 4], ["Opel", 2], ["Volkswagen", 2]],
}

def render_drilldown():
    if "drill_group" not in st.session_state:
        st.session_state.drill_group = None

    group = st.session_state.drill_group

    if group is None:
        options = {
            "xAxis": {"data": ["Animals", "Fruits", "Cars"]},
            "yAxis": {},
            "animationDurationUpdate": 500,
            "series": {
                "type": "bar",
                "id": "sales",                    # MISMO id en ambas vistas
                "data": [
                    {"value": 5, "groupId": "animals"},
                    {"value": 2, "groupId": "fruits"},
                    {"value": 4, "groupId": "cars"},
                ],
                "universalTransition": {"enabled": True, "divideShape": "clone"},
            },
        }
    else:
        sub = DRILLDOWN_DATA[group]
        options = {
            "xAxis": {"data": [item[0] for item in sub]},
            "yAxis": {},
            "animationDurationUpdate": 500,
            "series": {
                "type": "bar",
                "id": "sales",                    # MISMO id que arriba
                "dataGroupId": group,
                "data": [item[1] for item in sub],
                "universalTransition": {"enabled": True, "divideShape": "clone"},
            },
        }

    events = {
        "click": "function(p) { return p.data && p.data.groupId ? p.data.groupId : null }",
    }

    if group is not None:
        if st.button("← Back", key="drill_back"):
            st.session_state.drill_group = None
            st.rerun()

    result = st_echarts(
        options=options,
        events=events,
        height="500px",
        replace_merge="series",          # REQUERIDO para universalTransition
        key="drilldown_chart",
    )
    if result and result.chart_event and result.chart_event in DRILLDOWN_DATA:
        st.session_state.drill_group = result.chart_event
        st.rerun()
```

**Reglas del drilldown:**
- Mantener el mismo `"id"` en la serie entre ambas vistas
- Usar `"groupId"` en datos top-level y `"dataGroupId"` en la serie detalle
- Pasar `replace_merge="series"` para merge-mode (sin esto, `notMerge: true` destruye la animación)
- Reemplazar handlers `graphic.onclick` con `st.button`
- Omitir `universalTransition` en versiones anteriores a ECharts 5

---

## 7. Theming

### Opciones disponibles

| Valor | Comportamiento |
|---|---|
| `"streamlit"` (default) | Lee variables CSS de Streamlit (`--st-text-color`, etc.). Se adapta automáticamente a light/dark mode y a `.streamlit/config.toml`. **Usar siempre en dashboards.** |
| `"dark"` | Tema oscuro nativo de ECharts. No lee CSS de Streamlit. |
| `"light"` | Tema claro nativo de ECharts. |
| `""` (string vacío) | Sin tema — ECharts default (siempre light). |
| `{...}` (dict) | Registra un tema custom vía `echarts.registerTheme()`. |

```python
# Tema adaptativo (recomendado para producción)
st_echarts(options=options, theme="streamlit", key="chart")

# Tema custom
CUSTOM_THEME = {
    "color": ["#d50075", "#47db95", "#00bfff"],  # neon: pink, green, blue
    "backgroundColor": "#000000",
    "textStyle": {"color": "#ffffff"},
    "title":   {"textStyle": {"color": "#d50075"}},
    "legend":  {"textStyle": {"color": "#ffffff"}},
    "categoryAxis": {
        "axisLine":  {"lineStyle": {"color": "#333"}},
        "axisLabel": {"color": "#aaa"},
        "splitLine": {"lineStyle": {"color": "#1a1a1a"}},
    },
    "valueAxis": {
        "axisLine":  {"lineStyle": {"color": "#333"}},
        "axisLabel": {"color": "#aaa"},
        "splitLine": {"lineStyle": {"color": "#1a1a1a"}},
    },
}
st_echarts(options=options, theme=CUSTOM_THEME, key="neon_chart")
```

---

## 8. `key` — cuándo y por qué es obligatorio

- Sin `key`, Streamlit puede remontar el componente en cada rerun, perdiendo estado y reproduciendo animaciones de entrada.
- **Siempre usar `key`** en: charts con eventos, charts dentro de `@st.fragment`, charts con `replace_merge`, charts en loops.

```python
# Dentro de un loop — clave única por ítem
for i, cat in enumerate(categories):
    st_echarts(options=build_options(cat), key=f"chart_{cat}")
```

---

## 9. `@st.fragment` — cross-chart interaction sin reruns globales

Usar `@st.fragment` para secciones donde un click en un chart actualiza solo esa sección, sin rerenderizar la página completa.

```python
@st.fragment
def drill_section():
    # Chart principal con selección
    result = st_echarts(
        options=scatter_opts,
        on_select="rerun",
        selection_mode="points",
        key="scatter_main",
        theme="streamlit",
    )

    indices = result["selection"].get("point_indices", [])
    if indices:
        clicked_name = my_data[indices[0]][3]   # extraer nombre del punto
        # Chart de detalle reactivo
        st_echarts(
            options=build_detail_opts(clicked_name),
            key="scatter_detail",
            theme="streamlit",
        )
    else:
        st.info("Haz click en un punto para ver el detalle.")

# Llamar dentro de un container con borde opcional
with st.container(border=True):
    drill_section()
```

---

## 10. Showcase Dashboard — arquitectura y patrones

### Estructura recomendada

```
app.py
pages/
  showcase.py      ← dashboard principal
  demo_app.py      ← guía de API
  examples.py      ← catálogo de ejemplos
data/              ← CSVs, JSONs
demo_echarts/      ← módulos por categoría
  __init__.py
  bar.py
  line.py
  pie.py
  ...
```

### Patrón filtros + KPIs + charts

```python
import streamlit as st
import polars as pl
from streamlit_echarts import st_echarts, JsCode

# --- Carga con cache ---
@st.cache_data
def load_data():
    df = pl.read_csv("data/ventas.csv", encoding="latin1")
    df = df.with_columns(
        pl.col("fecha").str.strptime(pl.Date, format="%d-%m-%Y")
    )
    return df

df = load_data()

# --- Sidebar con filtros ---
with st.sidebar:
    periodo = st.selectbox("Período", ["1 Mes", "3 Meses", "12 Meses", "Todo"])
    mercados = st.multiselect("Mercado", df["mercado"].unique().to_list())

# --- Lógica de filtrado ---
max_date = df["fecha"].max()
offsets = {"1 Mes": "-1mo", "3 Meses": "-3mo", "12 Meses": "-1y"}
if periodo in offsets:
    start = pl.select(pl.lit(max_date).dt.offset_by(offsets[periodo])).item()
    current_df = df.filter(pl.col("fecha") >= start)
else:
    current_df = df

if mercados:
    current_df = current_df.filter(pl.col("mercado").is_in(mercados))

# --- KPIs con st.metric + sparklines ---
total = current_df["ventas"].sum()
orders = current_df["orden_id"].n_unique()

col1, col2 = st.columns(2)
with col1:
    spark = (
        current_df
        .with_columns(pl.col("fecha").dt.truncate("1mo").alias("mes"))
        .group_by("mes").agg(pl.col("ventas").sum())
        .sort("mes")["ventas"].to_list()
    )
    st.metric("Ventas Totales", f"${total:,.0f}", chart_data=spark, chart_type="area")

with col2:
    st.metric("Pedidos", f"{orders:,}")
```

### Patrón chart con tooltip JsCode y dataZoom

```python
opts = {
    "title":   {"text": "Tendencia de Ventas", "left": "center"},
    "tooltip": {
        "trigger": "axis",
        "valueFormatter": JsCode(
            "function(v){ return '$' + Math.round(v).toLocaleString(); }"
        ),
    },
    "legend":  {"bottom": "0"},
    "xAxis":   {"type": "category", "data": fechas},
    "yAxis":   {"type": "value"},
    "dataZoom": [
        {"type": "inside", "start": 0, "end": 100},
        {"type": "slider",  "start": 0, "end": 100, "height": 20, "bottom": 30},
    ],
    "grid":    {"bottom": "18%"},
    "series":  [
        {"name": "Ventas",    "type": "line", "smooth": True,
         "areaStyle": {"opacity": 0.1}, "data": ventas},
        {"name": "Ganancia",  "type": "line", "smooth": True, "data": ganancias},
    ],
}
st_echarts(options=opts, height="400px", key="trend", theme="streamlit")
```

### Patrón treemap con visualMap por margen

```python
tree_data = [
    {
        "name": categoria,
        "children": [
            {
                "name": sub,
                "value": [round(revenue, 2), round(margin, 1)],
            }
            for sub, revenue, margin in subcats
        ],
    }
    for categoria, subcats in data_by_cat.items()
]

opts = {
    "tooltip": {
        "formatter": JsCode(
            "function(p){"
            "var v=p.value; if(!v||v.length<2) return p.name;"
            "return p.name+'<br/>Rev: $'+v[0].toLocaleString()+'<br/>Margen: '+v[1].toFixed(1)+'%';"
            "}"
        )
    },
    "visualMap": {
        "type": "continuous",
        "min": -10, "max": 30,
        "inRange": {"color": ["#ee6666", "#fac858", "#91cc75"]},
        "dimension": 1,
        "orient": "horizontal", "left": "center", "bottom": "0%",
    },
    "series": [{
        "type": "treemap",
        "data": tree_data,
        "visibleMin": 300,
        "roam": False,
        "visualDimension": 1,
        "levels": [
            {"itemStyle": {"borderColor": "#555", "borderWidth": 3, "gapWidth": 3},
             "upperLabel": {"show": True, "height": 20, "color": "#fff"}},
            {"itemStyle": {"borderColor": "#aaa", "borderWidth": 1, "gapWidth": 1}},
        ],
    }],
}
st_echarts(options=opts, height="450px", key="treemap", theme="streamlit")
```

---

## 11. Catálogo de tipos de gráfico y sus patrones mínimos

### Bar básico

```python
{
    "xAxis": {"type": "category", "data": ["Lun", "Mar", "Mié"]},
    "yAxis": {"type": "value"},
    "series": [{"type": "bar", "data": [120, 200, 150]}],
}
```

### Bar horizontal apilado

```python
{
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
    "legend": {},
    "xAxis": {"type": "value"},
    "yAxis": {"type": "category", "data": categorias},
    "series": [
        {"name": s, "type": "bar", "stack": "total",
         "emphasis": {"focus": "series"}, "data": valores}
        for s, valores in series_dict.items()
    ],
}
```

### Line con área gradiente

```python
{
    "xAxis": {"type": "category", "boundaryGap": False, "data": fechas},
    "yAxis": {"type": "value"},
    "series": [{
        "type": "line", "smooth": True, "showSymbol": False,
        "lineStyle": {"width": 0},
        "areaStyle": {
            "opacity": 0.8,
            "color": JsCode(
                "new echarts.graphic.LinearGradient(0,0,0,1,"
                "[{offset:0,color:'rgb(128,255,165)'},{offset:1,color:'rgb(1,191,236)'}])"
            ).js_code,
        },
        "data": valores,
    }],
}
```

### Pie / Doughnut

```python
# Doughnut con borderRadius
{
    "tooltip": {"trigger": "item"},
    "legend": {"top": "5%", "left": "center"},
    "series": [{
        "type": "pie",
        "radius": ["40%", "70%"],
        "avoidLabelOverlap": False,
        "itemStyle": {"borderRadius": 10, "borderColor": "#fff", "borderWidth": 2},
        "label": {"show": False, "position": "center"},
        "emphasis": {"label": {"show": True, "fontSize": 40, "fontWeight": "bold"}},
        "labelLine": {"show": False},
        "data": [{"value": v, "name": n} for n, v in data.items()],
    }],
}
```

### Scatter con selección

```python
{
    "xAxis": {"type": "value", "name": "Eje X"},
    "yAxis": {"type": "value", "name": "Eje Y"},
    "tooltip": {
        "formatter": JsCode(
            "function(p){ return p.value[3]+'<br/>X: '+p.value[0]+'<br/>Y: '+p.value[1]; }"
        )
    },
    "visualMap": {
        "show": False, "dimension": 2,
        "min": 0, "max": max_size,
        "inRange": {"symbolSize": [10, 50]},
    },
    "series": [{
        "type": "scatter",
        "data": [[x, y, size, label], ...],
        "itemStyle": {"opacity": 0.7},
    }],
}
```

### Heatmap cartesiano

```python
{
    "tooltip": {"position": "top"},
    "xAxis": {"type": "category", "data": cols, "splitArea": {"show": True}},
    "yAxis": {"type": "category", "data": rows, "splitArea": {"show": True}},
    "visualMap": {"min": 0, "max": 10, "calculable": True,
                  "orient": "horizontal", "left": "center", "bottom": "15%"},
    "series": [{
        "type": "heatmap",
        "data": [[col_idx, row_idx, value], ...],
        "label": {"show": True},
        "emphasis": {"itemStyle": {"shadowBlur": 10}},
    }],
}
```

### Radar

```python
{
    "radar": {
        "indicator": [{"name": n, "max": m} for n, m in indicadores]
    },
    "series": [{
        "type": "radar",
        "data": [{"name": nombre, "value": valores_list}],
        "areaStyle": {"opacity": 0.1},
    }],
}
```

### Gauge de progreso

```python
{
    "series": [{
        "type": "gauge",
        "progress": {"show": True, "width": 18},
        "axisLine": {"lineStyle": {"width": 18}},
        "axisTick": {"show": False},
        "splitLine": {"length": 15, "lineStyle": {"width": 2, "color": "#999"}},
        "axisLabel": {"distance": 25, "color": "#999", "fontSize": 20},
        "anchor": {"show": True, "showAbove": True, "size": 25,
                   "itemStyle": {"borderWidth": 10}},
        "title": {"show": False},
        "detail": {"valueAnimation": True, "fontSize": 80, "offsetCenter": [0, "70%"]},
        "data": [{"value": 70}],
    }],
}
```

---

## 12. Errores comunes y soluciones

| Error | Causa | Solución |
|---|---|---|
| Chart se reanima en cada rerun | Sin `key=` | Agregar `key="nombre_unico"` |
| `universalTransition` no anima | Falta `replace_merge` o distintos `id` | Pasar `replace_merge="series"` y mismo `"id"` en la serie |
| JsCode no ejecuta | Olvidó `.js_code` al final | Usar `JsCode("...").js_code` |
| Gradiente no aplica | Mal constructor | Verificar `new echarts.graphic.LinearGradient(...)` |
| Chart en tab/expander con tamaño incorrecto | Streamlit aún no conoce dimensiones | Agregar `key=` único para forzar resize correcto |
| `result.chart_event` siempre None | Handler JS no retorna valor | Asegurarse que la función JS tenga `return` explícito |
| PyECharts sin tema oscuro | PyECharts usa ECharts 4 | Pasar el `options` como dict via `json.loads(chart.dump_options())` |
| Múltiples charts con mismo `key` | Colisión de estado | Usar keys únicos: `key=f"chart_{categoria}"` |

---

## 13. PyECharts — integración

```python
import json
import pyecharts.options as opts
from pyecharts.charts import Bar
from streamlit_echarts import st_echarts

bar = (
    Bar()
    .add_xaxis(["A", "B", "C"])
    .add_yaxis("Serie", [10, 20, 15])
    .set_global_opts(title_opts=opts.TitleOpts(title="Mi Bar"))
)

# Convertir a dict y pasar a st_echarts (permite theming y eventos)
st_echarts(options=json.loads(bar.dump_options()), theme="streamlit", key="pybar")
```

O usar `st_pyecharts` directamente:

```python
from streamlit_echarts import st_pyecharts
result = st_pyecharts(
    bar,
    events={"click": "function(p){ return p.name }"},
    key="pybar2",
)
```

---

## 14. Checklist antes de entregar un chart

- [ ] Todas las claves del dict están entre comillas
- [ ] `true/false/null` convertidos a `True/False/None`
- [ ] `series` preserva su forma original (dict vs lista)
- [ ] `key=` presente en todos los charts interactivos
- [ ] `JsCode("...").js_code` — con `.js_code` al final
- [ ] `theme="streamlit"` en dashboards de producción
- [ ] `replace_merge="series"` si se usa `universalTransition`
- [ ] `@st.fragment` para secciones con interacción cross-chart
- [ ] Solo las propiedades presentes en el source original — no agregar `grid`, `tooltip`, etc. de más