# Clasificación de producción — Tablero MPR (E10)

**Etapa:** 10 — Clasificación de Producción (pantalla única consolidada)
**Fecha:** 2026-07-03
**Capability:** `mpr-acciones-lote-tablero` (redefinida en Etapa 10)

> **Cambio de modelo (Etapa 10):** el **planchado deja de ser una etapa con stock**.
> Es un momento dentro de la producción (ahí se inspecciona) y **nunca deja saldo**.
> Las dos pantallas de la Etapa 9 (Inspección `Producción→Planchado/Scrap` y
> Clasificación `Planchado→2da/Semi`) se **reemplazan por una sola pantalla**
> «Clasificación de producción» que clasifica directo desde Producción.

---

## Descripción

La Etapa 10 consolida la clasificación de stock MPR en **una única pantalla de lote**,
accesible desde la barra global del Tablero de Producción mediante el botón
**«Clasificación de producción»**.

La clasificación sale directo de Producción:

```
Producción → { Semi Elaborado | 2da Selección | Desperdicio }
```

Como la carga puede hacerse días después (informe de fábrica), la pantalla pide
la **fecha de carga** del parte, que se propaga al asiento MSTOCK.

---

## Pantalla

### Clasificación de producción

- **URL:** `/mpr/tablero-produccion/clasificacion-produccion/`
- **Vista:** `ClasificacionProduccionView` (GET, `clasificacion_produccion.html`)
- **Origen:** depósito tipo `Produccion` (único)
- **Fecha:** selector nativo → hidden `dd/MM/yyyy` (obligatoria)
- **Destinos por componente:**
  - → `SemiElaborado` (prefijo POST: `semi_`)
  - → `2daSeleccion` (prefijo POST: `seg2da_`)
  - → `Scrap` / Desperdicio (prefijo POST: `scrap_`)
- **URL registro POST:** `/mpr/tablero-produccion/clasificacion-produccion/registrar/` (`clasificacion_produccion_registrar`)

---

## Servicios

### `construir_grilla_clasificacion_produccion(base_empresa)`
Retorna `{componentes: [...], componentes_vacio: bool}` con todos los componentes
que tienen `stock_deposito[art, Produccion] > 0` para la empresa.

### `_construir_grilla_transicion_lote(base_empresa, tipo_origen)` _(privado)_
Helper compartido:
1. Query directa `stock_deposito JOIN deposito WHERE tipo_mpr=tipo_origen AND saldo>0`
2. `_pivot_stock_por_tipo_mpr` para confirmar saldo real
3. `_fetch_descripciones_articulo` para código/descripción
4. Lista ordenada por `codigo_manual`

### `transferir_stock_lote(base_empresa, id_usuario, items, fecha=None)`
Batch best-effort. Cada `item`: `{id_articulo, tipo_origen, tipo_destino, cantidad}`.
El parámetro **`fecha`** (opcional) se propaga a `transferir_stock_entre_etapas`
para fechar el asiento MSTOCK (carga diferida). Si es `None`, usa la fecha del sistema.

```python
resultado = {
    "exitosas": int,        # items con ok=True
    "fallidas": int,        # items con ok=False o excepción
    "errores": [(id_art, mensaje), ...],
    "comprobantes": ["MSTOCK-XXXX-XXXXX", ...],
}
```

- **Sin `atomic()`**: cada transferencia es independiente (política E5/E7).
- **Best-effort**: un ítem fallido NO frena los demás.

### `transferir_stock_entre_etapas(..., fecha=None)`
Nuevo parámetro `fecha`. `fecha_mov = (fecha or date.today()).isoformat()`.

---

## Lógica de Bloqueo (BLOQUEO por fila)

Por cada fila del formulario:

1. La vista POST re-consulta el **stock real de Producción desde BD**
   (`_pivot_stock_por_tipo_mpr`). El `disponible_{id}` del cliente es **ignorado**.
2. Pre-check: si `(semi + 2da + scrap) > produccion_disponible` → `messages.error`
   en español, fila saltada.
3. Solo filas válidas se envían a `transferir_stock_lote(..., fecha=fecha_parte)`.
4. Alpine.js da feedback visual (ring rojo + submit deshabilitado) como UX auxiliar
   **no normativo** (la validación definitiva es server-side). El submit también se
   bloquea si falta la fecha.

---

## Campos POST (`RegistrarClasificacionProduccionView`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `fecha` | str `dd/MM/yyyy` | Fecha de carga del parte (obligatoria) |
| `semi_{id_articulo}` | Decimal | Cantidad a Semi Elaborado |
| `seg2da_{id_articulo}` | Decimal | Cantidad a 2da Selección |
| `scrap_{id_articulo}` | Decimal | Cantidad a Desperdicio |
| `disponible_{id_articulo}` | Decimal | Disponible reportado (ignorado; re-valida BD) |
| `csrfmiddlewaretoken` | str | CSRF token (obligatorio) |

---

## Comprobantes y Mensajes

- **Éxito:** `"N transferencia(s) registrada(s). Comprobantes: MSTOCK-…"` (`success`)
- **BLOQUEO por tope:** `"Producción insuficiente para artículo {id}: disponible {X}, solicitado {Y}. Fila ignorada."` (`error`)
- **Fecha inválida:** mensaje `error`, sin registrar.
- **Error individual (best-effort):** `"Error en artículo {id}: {mensaje}"` (`error`)

Todos los mensajes se consumen en la misma pantalla (no se filtran al tablero).

---

## Template

`mpr/templates/mpr/clasificacion_produccion.html` extiende `base_mpr.html` con la misma
estructura UX que **Parte de producción** (`parte_produccion.html`):

- Migas de pan, contenedor `mpr-contenedor-pagina`, encabezado compacto (título | fecha de carga + botón **Tablero** amber).
- Card blanca con **buscador predictivo** por código/descripción.
- Columna **Artículo** sticky (código + descripción); badge **En producción** con feedback en vivo «Clasificado: X u.».
- Columnas destino (**Semi elaborado**, **2da selección**, **Desperdicio**) con tintes alternados; captura **Docenas · Unidades** (1 docena = 12 u., igual que parte/OPP); validación `suma ≤ disponible`.
- Un solo botón **Guardar clasificación** en el pie; overlay `mpr-post-loading` al enviar.

Alpine.js:
- `clasificacionProduccion()` a nivel form: fecha nativa → hidden `dd/MM/yyyy`, `busqueda`, `hayExcedida`.
- `x-data` por fila con `cantSemi/cant2da/cantScrap`, `suma` y `excede`.

---

## URLs E10

```
/mpr/tablero-produccion/clasificacion-produccion/           → clasificacion_produccion
/mpr/tablero-produccion/clasificacion-produccion/registrar/ → clasificacion_produccion_registrar
```

URL E5 `mpr:transicion_lote` conservada sin exposición en UI (backward-safe).
Las URLs E9 (`inspeccion_lote`, `clasificacion_lote` y sus `registrar`) fueron **eliminadas**.

---

## Impacto en el pipeline (E1) y transiciones (E5)

- `mpr/pipeline.py`: `Planchado` **removido** de `ORDEN_ETAPAS_MPR` (7 etapas),
  `TIPOS_QUE_SUMAN_STOCK` y `TRANSICIONES_LEGALES`.
- Transiciones legales desde Producción: `→ SemiElaborado`, `→ 2daSeleccion`, `→ Scrap`.
- La constante `TIPO_MPR_PLANCHADO` y `get_deposito_planchado_mpr` se conservan
  **deprecadas** (backward-compat de imports) pero no participan del grafo.
- Tablero: se elimina la columna «Planchado» (9 columnas de pipeline).

---

## Fuera de alcance E10

- Migración de esquema MySQL (el depósito Planchado puede quedar sin uso; sin datos productivos).
- Tabla de auditoría agrupada por lote.
- Armado de packs (Terminado).
