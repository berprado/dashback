# 🚦 Flujo de inicio del Dashboard Operativo (Backstage)

> Documento de referencia: **lógica de arranque**, selección de dataset y comportamiento ante casos límite.

---

## 🧠 Idea central

Al iniciar la aplicación, el sistema **primero determina el contexto operativo** (qué operativa está vigente y en qué estado) y **después** decide:

- qué vista/dataset usar
- qué valores mostrar por defecto
- qué mensajes o estados de “sin datos” presentar

---

## 🧩 Definiciones clave

### 1) Operativa activa (modo Tiempo Real)
Una operativa se considera **activa** cuando:

- `ope_operacion.estado = 'HAB'`
- `ope_operacion.estado_operacion IN (22, 24)`
  - **22** → EN PROCESO
  - **24** → INICIO CIERRE

La aplicación selecciona la **más reciente** (mayor `id`).

### 2) Operativa cerrada (modo Histórico)
Una operativa se considera **histórica** cuando:

- `ope_operacion.estado = 'HAB'`
- `ope_operacion.estado_operacion = 23` → **CERRADO**

---

## ✅ Qué ocurre al iniciar la app

### Paso A — Buscar operativa activa
La app intenta encontrar una operativa activa (22/24).

**Resultados posibles:**

1. ✅ Existe operativa activa → Modo **Tiempo Real**
2. ❌ No existe operativa activa → Modo **Histórico**

---

## 🟢 Caso 1: existe operativa activa (22/24)

### Dataset utilizado
- `comandas_v6`

> Nota: el esquema depende de la DB activa definida en la URL de conexión; en el código se usan nombres no calificados.

> Esta vista ya está acotada a la **última operativa activa**.

### Qué se muestra al abrir
- Encabezado con operativa y estado:
  - *Operativa #<id> — EN PROCESO* o *INICIO CIERRE*
- KPIs y gráficos calculados sobre `comandas_v6`.

### 🧊 Caso especial: operativa activa pero todavía no hay ventas
Esto sucede cuando existe la operativa pero aún no hay comandas registradas.

**Comportamiento esperado (no es error):**

- KPIs en **cero**:
  - total vendido = 0
  - comandas = 0
  - ítems = 0
- Gráficos vacíos con texto:
  - *Aún no se registraron ventas en esta operativa.*
- Tabla detalle vacía.
- Estado informativo sugerido:
  - *🟢 Operativa activa — esperando primeras comandas.*

---

## 📚 Caso 2: NO existe operativa activa

### Cuándo pasa
- La última operativa está **CERRADO (23)**
- O no existe ninguna operativa activa (22/24)

### Dataset utilizado
- `comandas_v6_todas`

> Nota: el esquema depende de la DB activa definida en la URL de conexión; en el código se usan nombres no calificados.

⚠️ Importante: para histórico, la app **siempre debe aplicar filtros**, por ejemplo:

- rango de operativas (`id_operacion BETWEEN op_ini AND op_fin`)
- y/o rango de fechas (`fecha_emision BETWEEN dt_ini AND dt_fin`)

### Qué se muestra al abrir (recomendado)
- Banner:
  - *📚 No hay operativa activa — mostrando histórico.*
- Selector de operativas.
- Por defecto:
  - **última operativa cerrada** (23)

---

## ✅ Caso 3: la última operativa está CERRADO (23)

**Interpretación:**
- la operativa es **histórica**
- el dashboard debe abrir en modo **Histórico**

**Default recomendado:**
- `id_operacion = última operativa cerrada`

---

## 🧯 Casos límite y consideraciones importantes

### 1) Estado lógico vs estado de negocio

**Estado lógico** (validez del registro):
- `bar_comanda.estado` → HAB / DES
- `ope_operacion.estado` → HAB / DES

✅ Regla: el dashboard siempre debe mostrar **solo HAB**.

**Estado de negocio** (flujo operativo):
- `estado_comanda` (PENDIENTE, PROCESADO, ANULADO)
- `estado_impresion` (IMPRESO, PENDIENTE, NULL)
- `tipo_salida` (VENTA, CORTESIA)

✅ Regla: estos estados **no se filtran por defecto**, se usan como filtros UI.

---

### 2) Operativa activa “vacía”: ¿normal o problema?

- Normal al inicio de la noche.
- Si persiste demasiado puede indicar:
  - POS apuntando a otra DB
  - `id_operacion` inconsistente al registrar comandas

El dashboard mostrará *cero ventas*. Si no debería ser cero, es alerta operativa.

---

### 3) Dos operativas activas por error

Con la lógica actual:
- se elige la operativa activa con mayor `id`.

Esto evita bloquear la app, pero conviene control administrativo para evitar el caso.

---

## 🧾 Resumen en forma IF/ELSE

1. Buscar operativa activa (22/24):
   - si existe → **Tiempo real** con `comandas_v6`
     - si no hay ventas → KPIs=0 + mensajes “sin ventas aún”
2. Si no existe operativa activa:
   - **Histórico** con `comandas_v6_todas`
   - por defecto: última operativa cerrada (23)
   - si no hay operativas cerradas → mostrar “sin datos” y pedir selección de rango

---

✨ *Este documento captura la lógica de arranque y garantiza consistencia entre modo tiempo real e histórico.*
