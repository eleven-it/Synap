# Envío a Producción desde el Tablero — MPR Etapa 7

**Fecha:** 03/07/2026 — **actualizado 27/07/2026** (límite de filas del Tablero Par/Pack)  
**Change:** `mpr-pipeline-etapa7-enviar-desde-tablero`  
**Capability:** `mpr-envio-produccion-tablero`  
**Artefactos SDD:** Proposal, Spec, Design #1024, Tasks #1025  

**Límite UI:** `TableroProduccionView` pide `limit=500` a `listar_tablero_por_articulo` / `listar_tablero_pack`. Filas más allá de ese tope (ordenadas por resta urgente) no se muestran ni se incluyen en el POST de Enviar. Antes era 200; con ~288 componentes en planta se cortaban filas con `a_enviar > 0` (p. ej. Gmel fuera del top 200).

---

## Propósito

La Etapa 7 introduce la capacidad de **enviar componentes directamente a producción desde el Tablero de Demanda Consolidado**, sin pasar por el wizard/OPT. El ledger vive en **`mpr_envio_produccion` (MySQL)**. No escribe en `stock_deposito` ni `movimiento_stock`.

El envío contribuye a la columna **Enviado** del tablero mediante la fórmula E7:

```
Enviado[comp] = Enviado_OPT[comp] + Enviado_tablero[comp]
Enviado_tablero[comp] = max(0, SUM(envíos_tablero) − acreditado[comp])
acreditado = max(stock_componente, clasificado_desde_producción, partes_acumulados)
stock_componente = Producido + Semi + 2da + Scrap
clasificado_desde_producción = SUM(mpr_transicion_lote.cantidad WHERE tipo_origen = 'Produccion')
```

Los **componentes** del tablero no usan depósito **Terminado** (el armado mueve el pack). La columna Terminado no se muestra en el tablero de producción.

Al clasificar desde Producido, el stock en Semi/2da/Scrap sigue acreditando envíos. Si el semi ya salió por armado del pack, la trazabilidad en `mpr_transicion_lote` evita que **Fabricando repunte** al vaciar el pipeline físico.

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

**Vista:** `EnviarProduccionLoteView(MprLoginRequiredMixin, MprEscritorioVerMixin, View)`  
**URL:** `POST /mpr/tablero-produccion/enviar/` → `mpr:tablero_produccion_enviar`

**Permiso:** solo `mpr.ver`. Usuarios con únicamente `mpr.tablero_ver` reciben 403 (el tablero es solo lectura para ellos; la UI oculta el formulario de envío vía `puede_enviar` / `solo_lectura_tablero`).

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
<input form="form-enviar-lote" type="hidden" name="pendiente_{{ fila.id_articulo }}" value="{{ fila.a_enviar }}">

{# Botón en barra de encabezado #}
<button form="form-enviar-lote" type="submit" @click.prevent="...confirm...">
    Enviar a producción
</button>
```

Los modales E5 conservan sus propios `<form method="post">` sin interferencia.

### Columna "Enviar" (col 11)

- Un solo input entero por fila (`type="number"`, `step="1"`, sin decimales).
- **Modo docenas:** campo `envio_{id}_docenas`; se prellena con **`a_enviar_docenas_pcp`** (docenas enteras = pares ÷ 12 redondeado). El POST convierte a pares con `docenas × 12` (ignora pares sueltos).
- **Modo pares:** campo `envio_{id}` con cantidad en pares enteros; se prellena con **`a_enviar`**.
- Si el tope en la unidad mostrada es 0 (`a_enviar_docenas_pcp = 0` en docenas, o `a_enviar = 0` en pares), el input queda vacío y **deshabilitado**.
- `max` del input = tope (`a_enviar` / docenas PCP); JS recorta cualquier valor mayor.
- **Tope:** `a_enviar = MAX(0, MIN(resta_urgente − Σ envíos ledger, resta_total))`. El ledger **siempre** descuenta el tope, también cuando Fabricando = 0 (p. ej. stock de pipeline preexistente absorbe envíos). **No** se reabre el tope a `resta_urgente` en ese caso: eso generaba reenvíos fantasma sin subir Fabricando. El servidor **ajusta al tope** si el POST lo supera (ya no envía de más).
- **Fabricando vs stock:** `Fabricando = max(0, Σ envíos − acreditado)`. Si hay stock en Producido/Semi/2da/Scrap mayor que los envíos, Fabricando queda en 0 aunque el Enviar haya grabado filas en el ledger.
- Hidden `presentacion`, `pendiente_*` / `resta_urgente_*` (con `a_enviar`) para parseo y warnings de sobreenvío en POST.
- Al confirmar, JavaScript copia **todas** las filas con cantidad > 0 como campos ocultos dentro de `#form-enviar-lote` (evita pérdida de líneas con el atributo HTML5 `form=`).
- El servidor omite cantidades ≤ 0.
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

### Limpiar entorno de pruebas (UAT / desarrollo)

Para vaciar ledgers MPR y stock en depósitos `tipo_mpr` antes de una corrida de prueba:

```bash
docker exec Synap_app python manage.py limpiar_historico_mpr --base-empresa=administranet96 --dry-run
docker exec Synap_app python manage.py limpiar_historico_mpr --base-empresa=administranet96 --confirm
```

Borra: `mpr_envio_produccion`, partes, transiciones, armado surtido, roster. **No** toca `mpr_config`, `mpr_turno` ni pedidos PED / demanda en vivo.

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

## Permisos y perfiles (tablero)

| Acción / URL | `mpr.ver` | `mpr.tablero_ver` (sin `mpr.ver`) |
|--------------|-----------|-----------------------------------|
| GET `/mpr/tablero-produccion/` | Sí (completo) | Sí (solo lectura) |
| POST `/mpr/tablero-produccion/actualizar/` | Sí | Sí |
| GET `/mpr/manual/` | Sí | Sí |
| POST `/mpr/tablero-produccion/enviar/` | Sí | **403** |
| GET envíos / POST anular | Sí (supervisor) | **403** |
| GET clasificación / POST registrar | Sí | **403** |
| Menú MPR | Completo | Solo «Tablero de producción» |

Perfil **operario + tablero:** `mpr.parte_operario` + `mpr.tablero_ver`, sin `mpr.ver`. Landing en `/mpr/mi-parte/`; consulta demanda en el tablero sin mutar ledger ni abrir CC/reportes. Flags de contexto: `puede_enviar=False`, `solo_lectura_tablero=True`.

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
