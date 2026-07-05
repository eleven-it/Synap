# Envío a Producción desde el Tablero — MPR Etapa 7

**Fecha:** 03/07/2026  
**Change:** `mpr-pipeline-etapa7-enviar-desde-tablero`  
**Capability:** `mpr-envio-produccion-tablero`  
**Artefactos SDD:** Proposal, Spec, Design #1024, Tasks #1025  

---

## Propósito

La Etapa 7 introduce la capacidad de **enviar componentes directamente a producción desde el Tablero de Demanda Consolidado**, sin pasar por el wizard/OPT. El ledger vive en **`mpr_envio_produccion` (MySQL)**. No escribe en `stock_deposito` ni `movimiento_stock`.

El envío contribuye a la columna **Enviado** del tablero mediante la fórmula E7:

```
Enviado[comp] = Enviado_OPT[comp] + Enviado_tablero[comp]
Enviado_tablero[comp] = max(0, SUM(envíos_tablero) − stock_pipeline[comp])
stock_pipeline = Producido + Semi + 2da + Scrap + Terminado
```

Al clasificar desde Producido, el stock en Semi/2da/Scrap sigue acreditando envíos: **Fabricando no repunta** al vaciar Producido.

---

## Modelo: `MprEnvioProduccion`

**Archivo:** `mpr/models.py`  
**Migración:** `mpr/migrations/0014_mprenvio_produccion.py`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | BigAutoField (PK) | Autonumérico implícito |
| `base_empresa` | CharField(64) | Scope por empresa (AdministraNET) |
| `id_articulo` | IntegerField | ID artículo nivel COMPONENTE (ya explotado, no PACK) |
| `cantidad` | DecimalField(15,2) | Cantidad enviada |
| `id_usuario` | IntegerField | ID usuario AdministraNET |
| `creado_en` | DateTimeField(auto_now_add) | Timestamp de creación |
| `anulado` | BooleanField(default=False) | True si fue anulado (solo admin Django en E7) |

**Índices:** `mpr_ep_emp_art_idx` (base_empresa, id_articulo) y `mpr_ep_emp_fecha_idx` (base_empresa, creado_en).

---

## Servicios

### `_query_enviado_tablero_componente(base_empresa, comp_ids)`

**Archivo:** `mpr/services.py`

- Suma `cantidad` WHERE `anulado=False` AND `id_articulo IN comp_ids`.
- Retorna `{id_articulo: Decimal}`.
- **Backward-safe:** retorna `{}` si `comp_ids` vacío, `base_empresa` vacío o sin registros.

### `enviar_a_produccion_lote(base_empresa, id_usuario, items, pendientes=None)`

**Archivo:** `mpr/services.py`

- `items`: lista de `(id_articulo: int, cantidad: Decimal)`.
- `pendientes`: mapa `{id_articulo: Decimal}` para warnings de sobreenvío (opcional).
- Crea N registros `MprEnvioProduccion` en `transaction.atomic()` via `bulk_create`.
- **Omite** filas con `cantidad <= 0` (warning, no error).
- **Warning** no-bloqueante si `cantidad > pendiente` (envía de todas formas).
- **Ledger-only:** NO escribe en MySQL legacy ni en `stock_deposito`.
- Retorna `(ok: bool, n_creados: int, warnings: List[str], error: str|None)`.

---

## Vista y URL

**Vista:** `EnviarProduccionLoteView(MprLoginRequiredMixin, View)`  
**URL:** `POST /mpr/tablero-produccion/enviar/` → `mpr:tablero_produccion_enviar`

**Flujo POST:**

1. Parsea inputs `envio_{id_art}` (cantidad) y `pendiente_{id_art}` del body.
2. Llama `enviar_a_produccion_lote(...)`.
3. Mensaje de éxito con conteo + warnings (si los hay).
4. Redirect a `mpr:tablero_produccion?{filtros_qs}` (preserva filtros de fecha y solo_pendiente).

---

## UI en el Tablero

### Anti-form-nesting (HTML5 `form=` attribute)

El tablero ya tiene `<form method="post">` dentro de cada `<td>` (modal transición E5). Forms anidados son HTML inválido. Solución:

```html
{# Form fantasma FUERA de la tabla, antes de </section> #}
<form id="form-enviar-lote" method="post" action="{% url 'mpr:tablero_produccion_enviar' %}">
    {% csrf_token %}
    <input type="hidden" name="filtros_qs" value="...">
</form>

{# En cada <tr> — input con atributo form= #}
<input form="form-enviar-lote" type="number" name="envio_{{ fila.id_articulo }}" data-envio-qty ...>
<input form="form-enviar-lote" type="hidden" name="pendiente_{{ fila.id_articulo }}" value="{{ fila.pendiente }}">

{# Botón en barra de encabezado #}
<button form="form-enviar-lote" type="submit" @click.prevent="...confirm...">
    Enviar a producción
</button>
```

Los modales E5 conservan sus propios `<form method="post">` sin interferencia.

### Columna "Enviar" (col 11)

- Input numérico (`type="number"`, `step="1"`) editable en todas las filas; se prellena con `pendiente` cuando es > 0.
- Al confirmar, JavaScript copia **todas** las filas con cantidad > 0 como campos ocultos dentro de `#form-enviar-lote` (evita pérdida de líneas con el atributo HTML5 `form=`).
- El servidor omite cantidades ≤ 0; warning no bloqueante si cantidad > pendiente.

---

## Fórmula de Enviado — Sin doble conteo

```
SUM(envíos_tablero) = 30   →   Si stock_prod = 0:  Enviado_tablero = 30
SUM(envíos_tablero) = 30   →   Si stock_prod = 20: Enviado_tablero = 10
SUM(envíos_tablero) = 10   →   Si stock_prod = 15: Enviado_tablero = 0  (clamp >= 0)
```

Cuando los envíos del tablero generan un parte y ese parte escribe `stock_produccion`, la fórmula `max(0, envíos - stock_prod)` absorbe la diferencia automáticamente. Sin doble conteo.

### Caso "doble camino" activo (tablero + OPT)

Si un mismo componente recibe envíos por ambas vías (tablero directo + OPT wizard):

```
Enviado = Enviado_OPT + Enviado_tablero
```

Ambas contribuciones son aditivas y no se solapan. Documentar al equipo que en E7 existe un único camino recomendado por componente para evitar confusión operativa (tema para E8).

---

## Casos de Uso

| Caso | Comportamiento |
|------|---------------|
| 3 filas con cantidad > 0 | Crea 3 registros, mensaje "3 componentes enviados a producción." |
| Alguna cantidad = 0 o negativa | Se omite con warning, no falla |
| Cantidad > pendiente | Warning de sobreenvío, envío se ejecuta igual |
| Lote vacío (ninguna cantidad ingresada) | Redirige sin crear registros, sin error |
| Sin empresa activa en sesión | Redirige al tablero con mensaje de error |
| Backward-safe: tabla vacía | `Enviado_tablero = 0`, tablero idéntico a E6 |

---

## Anulación de Envíos (E7)

En Etapa 7, la anulación es solo vía **admin Django** (campo `anulado=True`). La UI de anulación está diferida a E8.

`/admin/mpr/mprenvioproduccion/`

---

## Tests

**Archivo:** `mpr/tests/test_etapa7_enviar_tablero.py`  
**Comando:** `docker exec Synap_app python manage.py test mpr.tests.test_etapa7_enviar_tablero --keepdb --noinput`

| Clase | Descripción |
|-------|-------------|
| `TestMprEnvioProduccionModelo` | Creación, campos, defaults, __str__, índices |
| `TestEnviarProduccionLote` | Lote válido, omite qty<=0, warning sobreenvío, vacío, ledger-only |
| `TestQueryEnviadoTableroComponente` | Suma no-anulados, filtra comp_ids, backward-safe |
| `TestIntegracionEnviadoTablero` | listar_tablero: fórmula dos fuentes, max(0,...), backward-safe |
| `TestEnviarProduccionLoteView` | POST 302, crea registros, preserva filtros, sin empresa |

**Suite no-regresión:** `docker exec Synap_app python manage.py test mpr --keepdb --noinput` (348 tests, 0 fallos).

---

## Archivos Modificados/Creados

| Archivo | Acción |
|---------|--------|
| `mpr/models.py` | + clase `MprEnvioProduccion` |
| `mpr/migrations/0014_mprenvio_produccion.py` | Migración additive (CreateModel + AddIndex x2) |
| `mpr/services.py` | + `_query_enviado_tablero_componente`, + `enviar_a_produccion_lote`, + paso 7b en `listar_tablero_por_articulo` |
| `mpr/views.py` | + `EnviarProduccionLoteView` |
| `mpr/urls.py` | + `path('tablero-produccion/enviar/', ...)` |
| `mpr/templates/mpr/tablero_produccion.html` | + col Enviar, + form fantasma, + botón, colspan 11→12 |
| `mpr/tests/test_etapa7_enviar_tablero.py` | Nuevo — 26 tests |
| `mpr/tests/test_tablero_consolidado.py` | + mock `_query_enviado_tablero_componente` backward-safe |
| `mpr/tests/test_opp_parte_etapa4.py` | + mock `_query_enviado_tablero_componente` backward-safe |
| `docs/mpr/TABLERO_CONSOLIDADO.md` | + sección Enviado E7 + col Enviar |
| `docs/mpr/ENVIO_PRODUCCION_TABLERO.md` | Nuevo — esta doc |

---

## Fuera de Alcance (E7)

- Vínculo envío↔parte (qué parte consumió qué envío tablero)
- Comprobante MSTOCK para envíos tablero
- Parte component-level directo desde tablero
- Deprecación del wizard/OPT para el flujo de envío

---

## Anulación de envíos (Opción A — supervisor)

**Fecha:** 05/07/2026  
**URLs:** `GET /mpr/tablero-produccion/envios/` · `POST /mpr/tablero-produccion/envios/anular/`

### Propósito

Permite a supervisores corregir envíos duplicados o erróneos del tablero marcando filas en `mpr_envio_produccion` como `anulado=1`. **No revierte stock físico** en depósitos; solo ajusta el ledger (Pendiente, Fabricando, Enviado).

### Reglas de negocio

| Condición | Requisito |
|-----------|-----------|
| `anulado = 0` | Sí |
| `codigo_movimiento_mstock IS NULL` | Sí |
| Permiso supervisor / admin MPR | Sí |
| FIFO vs partes | Partes registradas **desde el primer envío tablero activo** consumen envíos más antiguos primero |
| Anulación parcial por fila | **No** (MVP: fila completa o nada) |

### Esquema MySQL (auditoría)

Columnas añadidas idempotentemente por `run_mpr_core_tables_mysql`:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `anulado_en` | DATETIME NULL | Timestamp de anulación |
| `id_usuario_anula` | INT NULL | Usuario que anuló |

### Servicios

- `listar_envios_produccion_anulables(base, limit=200, id_articulo=None, incluir_anulados=False)` — lista con saldo anulable FIFO.
- `anular_envios_produccion_seleccionados(base, ids, id_usuario)` — valida y anula filas completas.

### Tests

`mpr/tests/test_envios_anulacion.py` — FIFO, agrupación por lote, integración MySQL.

### UI

- Enlace **Anular envíos** en el tablero (solo supervisores).
- **Filtro obligatorio por fecha** del envío (`DATE(creado_en)`).
- Lista de **lotes** (agrupados por `uuid_lote`; legacy por usuario + segundo).
- Al expandir un lote, se muestran las **líneas** con checkbox para anular.

### Esquema — uuid_lote

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `uuid_lote` | CHAR(36) NULL | Mismo UUID para todas las líneas de un `crear_envios_lote` |

### Servicios

- `listar_lotes_envios_produccion_anulables(base, fecha, ...)` — lotes con líneas y saldo FIFO.
- `anular_envios_produccion_seleccionados(base, ids, id_usuario)` — valida y anula filas completas.
