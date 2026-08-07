# Inventario físico Synap (conteo ciego)

Módulo de **inventario físico / conteo ciego** migrado desde `Inventario.frm` (VB6). Distinto de la **consulta pivote MPR** en [`/stock/inventario/`](INVENTARIO_TABLA_MPR.md) (`stock-inventario-tabla`).

## Alcance MVP

- Campañas mensuales en depósitos MPR (`Terminado`, `2daSeleccion`).
- Solo artículos con `articulo.tipo_art_fab` en **`Terminado`**, **`Tercero`** o **`Fabricado 2da`** (excluye Fabricado y vacíos). Los `Tercero` son producto final comprado, almacenable y vendible, y se tratan junto a Terminados.
- Conteo ciego offline-first (PWA Nivel A) con sync idempotente.
- Analizador supervisor con diferencia `contado − snapshot` (columna UI **Disponible**, campo interno `saldo_snapshot`) y **ajuste post-snapshot** (ver sección siguiente).
- **Ajuste post-snapshot (implementado):** gap de movimientos posteriores al snapshot; MSTOCK usa **Diferencia real**. Detalle en [`PLAN_AJUSTE_POST_SNAPSHOT_INVENTARIO_FISICO.md`](PLAN_AJUSTE_POST_SNAPSHOT_INVENTARIO_FISICO.md).
- Cantidades en UI (disponible, contado, diferencia, eventos) se muestran como **enteros** (sin decimales); el ingreso móvil usa `inputmode="numeric"` y validación JavaScript ≥ 0.
- Autorización explícita y posteo MSTOCK vía `core/services/administranet_stock.py` (Faltante=3 / Sobrante=4).
- **Sin** volcado automático a tablas legacy `inventario*` (fase 2 opcional).

## Arquitectura

### Datos (MySQL empresa)

| Tabla | Rol |
|-------|-----|
| `inv_fisico_campana` | Cabecera: fecha, estado, depósitos JSON, contadores, `id_movimiento_mstock` |
| `inv_fisico_linea` | Proyección artículo×depósito: `saldo_snapshot`, `cantidad_contada`, `diferencia` (privados al contador); columnas de ajuste post-snapshot (`ajuste_sistema`, `ajuste_manual`, `diferencia_real`, …) solo supervisor |
| `inv_fisico_evento` | Ledger append-only con `client_event_id` UNIQUE (sync idempotente) |
| `inv_fisico_ajuste_auditoria` | Historial override / recalc / autorización MSTOCK por línea |

DDL idempotente: `stock/sql/001_inv_fisico_tables.sql` + `002_inv_fisico_ajuste_post_snapshot.sql` → proveedor `run_stock_inv_fisico_tables_mysql` en `core/services/legacy_mysql_schema/catalog.py`. Índice opcional en tabla legacy `stock`: proveedor `stock_indice_fechacontrol` (`idx_stock_dep_fechactrl` sobre `CodDeposito`, `FechaControl`).

### Estados de campaña

```
Borrador → EnConteo → EnRevision → Autorizado → Aplicado
                ↓           ↓            ↓
             Anulado    Anulado      Anulado (no desde Aplicado)
```

Reconteo ciego: `EnRevision → EnConteo`.

### Servicio principal

`stock/services/inventario_fisico.py`:

- Campañas, snapshot desde `stock_deposito.saldo` con **INNER JOIN** a `articulo` y filtro `tipo_art_fab`, sync batch, analizador.
- `calcular_diferencia(contado, snapshot)` = contado − snapshot (legacy; contador no la ve).
- **Ajuste post-snapshot:** funciones puras `ajuste_efectivo`, `calcular_disponible_ajustado`, `calcular_diferencia_real`, `hay_descuadre`; persistencia en `inv_fisico_linea`; auditoría en `inv_fisico_ajuste_auditoria`.
- `autorizar_y_aplicar_campana`: recalc fresco → bloqueo sync → Autorizado → MSTOCK por **diferencia_real** → Aplicado.
- `anular_campana`: Borrador/EnConteo/EnRevision sin MSTOCK.

### Ajuste post-snapshot (supervisor)

**Fuente de movimientos:** tabla legacy `stock` (renglones por artículo×depósito), filtrada por `CodDeposito IN depósitos de campaña`, `FechaControl >= inv_fisico_campana.fecha_snapshot` y `Anulado <> 'Si'`. Campo temporal **autoritativo = `stock.FechaControl`** (TIMESTAMP de inserción; no usar `stock.Fecha` ni solo la cabecera `movimiento_stock`). Desglose en detalle de línea con JOIN opcional a `movimiento_stock` para motivo/comprobante.

**Fórmulas:**

```
Cargado después (ajuste_sistema) = Σ (Entrada − Salida) post-snapshot por artículo×depósito
Ajuste efectivo                  = ajuste_manual si existe; si no, ajuste_sistema
Disponible ajustado              = saldo_snapshot + ajuste_efectivo
Diferencia real                  = cantidad_contada − disponible_ajustado  (NULL si no contado)
Saldo final (UI)                 = saldo_actual_ref + diferencia_real  (NULL si no contado)
                                 → saldo previsto en stock_deposito tras autorizar MSTOCK
```

**Control de descuadre:** `saldo_actual_ref` = `stock_deposito.saldo` al recalcular; si difiere de `snapshot + ajuste_sistema`, el analizador muestra aviso (no bloquea). Sin descuadre, **Saldo final** coincide con **Contado**.

**Flujo refresh / override / autorizar:**

1. Al abrir analizador (estado no final): `recalcular_ajuste_post_snapshot(pisar_overrides=False)`.
2. Botón **Actualizar ajustes post-snapshot** → POST `/stock/api/campana/<id>/ajuste/recalcular/`; modal Synap si hay overrides (conservar vs reemplazar).
3. Override por línea → POST/DELETE `/stock/api/campana/<id>/linea/<id_linea>/ajuste/` + auditoría.
4. Detalle línea → GET movimientos post-snapshot; tabla con fecha dd/MM/yyyy.
5. **Autorizar** → recalc preservando overrides → MSTOCK solo líneas con `cantidad_contada IS NOT NULL` y `diferencia_real <> 0` (motivo 3 Faltante / 4 Sobrante por signo).

**APIs nuevas (permiso `gestionar`):**

| Ruta | Método | Acción |
|------|--------|--------|
| `/stock/api/campana/<id>/ajuste/recalcular/` | POST | Recalcular ajustes (`pisar_overrides` opcional) |
| `/stock/api/campana/<id>/linea/<id_linea>/ajuste/` | POST / DELETE | Guardar / quitar override |
| `/stock/api/campana/<id>/linea/<id_linea>/movimientos/` | GET | Desglose movimientos post-snapshot |
| `/stock/api/campana/<id>/marcar-no-contados-cero/` | POST | Marcar masivamente **Contado = 0** en líneas sin contar (toda la campaña) |

### Rutas

| Ruta | Permiso | Descripción |
|------|---------|-------------|
| `/stock/inventario-fisico/` | `stock.inventario_fisico.gestionar` | Listado campañas |
| `/stock/inventario-fisico/nueva/` | gestionar | Alta campaña + snapshot |
| `/stock/inventario-fisico/<id>/monitor/` | gestionar | Progreso, conflictos, cierre conteo |
| `/stock/inventario-fisico/<id>/analizador/` | gestionar | Diferencias, filtros faltante/sobrante, marcas y búsqueda en tabla |
| `/stock/inventario-fisico/<id>/linea/<id_linea>/` | gestionar | Detalle eventos por línea |
| `/stock/conteo/` | `stock.inventario_fisico.contar` | PWA operario |
| `/stock/api/conteo/prefetch/` | contar | Catálogo ciego |
| `/stock/api/conteo/registrados/` | contar | Artículos ya contados del depósito (ciego) |
| `/stock/api/conteo/sync/` | contar | Sync batch |
| `/stock/api/campana/<id>/autorizar/` | `stock.inventario_fisico.autorizar` | Autorizar + MSTOCK |

### Crear campaña y asignar contadores (supervisor)

UI alineada al canon `/stock/inventario/` (cabecera `rounded-lg border border-slate-700 bg-slate-800`, eyebrow `Stock · …`, contenedor `mx-auto flex w-full min-w-0 max-w-none flex-col … pb-24`).

**Pantalla de alta (`crear.html`)** en una sola vista con secciones:

1. **Fecha y depósitos** — `input[type=date]` (se registra como dd/MM/yyyy) + checkboxes de depósitos MPR elegibles. Al crear se toma el snapshot de saldos por artículo.
2. **Asignar contadores** — lista de usuarios con buscador (checkboxes `name=contadores`) obtenida de `listar_contadores_candidatos()` (reutiliza `mpr.services_operario.listar_usuarios`). Fallback: campo `contadores_texto` con IDs AdministraNET separados por coma. El permiso `stock.inventario_fisico.contar` se valida al abrir la app móvil.
3. **CTA**:
   - **Guardar borrador** (`accion=crear_borrador`) → crea en `Borrador`.
   - **Crear y abrir conteo** (`accion=crear_abrir`) → crea, asigna contadores y transiciona a `EnConteo`. Si no hay contadores, queda en `Borrador` con aviso.

**Reasignar contadores (`monitor.html`)** — modal Synap (sin diálogos nativos) con `accion=reasignar` que invoca `asignar_contadores()`. Disponible en `Borrador`, `EnConteo` y `EnRevision`. Los chips «Contadores asignados» muestran `código · nombre` vía `etiquetar_contadores()`.

**Listado (`listado.html`)** — tabla densa con fecha dd/MM/yyyy, badge de estado por color, cantidad de depósitos, barra de avance (`obtener_progreso_campana`), chips de contadores y accesos Monitor/Analizador.

**Contrato de vistas / servicio:**

| Función servicio | Rol |
|------------------|-----|
| `parse_ids_contadores(valores)` | Normaliza IDs (lista POST + CSV) a ints únicos ordenados |
| `listar_contadores_candidatos(base_empresa)` | Usuarios candidatos `{id_usuario, cod_usuario, nombre_completo}` |
| `etiquetar_contadores(ids, candidatos)` | Enlaza ids asignados a su etiqueta legible |

`inventario_fisico_crear_view` acepta `contadores` (lista) + `contadores_texto` y `accion` (`crear_abrir`/`crear_borrador`); `inventario_fisico_monitor_view` acepta `accion=reasignar`.

**Analizador (`analizador.html`)** — filtros de diferencia (Todas / Faltante / Sobrante / Con diferencia / **No contados**) vía GET `filtro` sobre **Diferencia real** o `cantidad_contada IS NULL` (`no_contados`); columnas **Disponible** (`saldo_snapshot`), **Cargado después**, **Disponible ajustado**, **Contado**, **Diferencia real**, **Saldo final** (previsto post-MSTOCK), **Contador**; chip «manual» en override; ícono descuadre; botón **Actualizar ajustes post-snapshot** (modales Synap, sin `alert`/`confirm`/`prompt`); multi-marca con tags (`marcas_incluidos`, catálogo `listar_marcas_catalogo`, artículo `CodigoMarca`); botón **Aplicar filtros** envía GET preservando `filtro`. Búsqueda **Buscar en tabla** filtra en vivo (Alpine) por código y nombre sobre filas ya cargadas. **Saldo final** es solo lectura/UI: no modifica conteos ni escribe stock. Contado **0** no entra en «No contados» (es conteo explícito). Chip **`N no contados`** (N = campaña completa, sin filtro de marcas) y acción **Marcar no contados como 0** cuando el supervisor tiene permiso `gestionar` y la campaña está en **EnConteo** o **EnRevision** (ver sección siguiente).

#### Marcar no contados como 0 (masivo)

Acción supervisora en el analizador para asignar **Contado = 0** a todas las líneas con `cantidad_contada IS NULL` que aún no fueron contadas. Cierra el gap operativo cuando el equipo confirma que los artículos no encontrados deben registrarse como cero antes de autorizar MSTOCK.

**Alcance:** **toda la campaña**. El chip «N no contados», el desglose del modal y la marca masiva **ignoran** el filtro de marcas activo en la tabla del analizador. El modal aclara explícitamente que la acción aplica a **toda la campaña**, no solo a las filas visibles.

**Precondiciones:**

| Condición | Comportamiento |
|-----------|----------------|
| Permiso `stock.inventario_fisico.gestionar` | Obligatorio; sin él la API responde 403 y el botón no se muestra |
| Estado campaña **EnConteo** o **EnRevision** | Permitido; otros estados → 400 en español, sin cambios |
| Líneas ya contadas (`cantidad_contada IS NOT NULL`) | No se modifican (incluye Contado = 0 explícito) |
| Sync móvil concurrente | Si un operario sincroniza cantidad &gt; 0 antes de proyectar, la línea **no** queda en 0 (condición `IS NULL` prevalece) |

**Qué hace (por línea marcada):**

1. `_proyectar_linea(..., cantidad=0, solo_si_sin_contar=True)` → `cantidad_contada=0`, `estado_linea='Contado'`, recálculo de diferencia cruda.
2. Un `inv_fisico_evento` append-only con `client_event_id` = UUID canónico (**36 caracteres**, `str(uuid.uuid4())`), `cantidad=0`, `resultado=aceptado`, `motivo` fijo en español: **`Supervisor: no encontrado / contado 0`**.
3. Una fila en `inv_fisico_ajuste_auditoria` con `accion='contado_cero_masivo'`.

**Qué no hace:** no ejecuta MSTOCK, no recrea snapshot, no altera líneas ya contadas, no cambia el estado de la campaña a Aplicada/Autorizado.

**UI (modal Synap, sin `alert`/`confirm`/`prompt`):**

- Título: «Marcar líneas sin contar como 0».
- Texto: asignará Contado = 0 a **N** línea(s) de **toda la campaña**; no modifica lo ya contado; no aplica MSTOCK.
- **Desglose previo:** total no contados; cuántas tienen `saldo_snapshot ≠ 0`; cuántas tienen movimiento post-snapshot neto ≠ 0 (`lineas_con_snap_ne0`, `lineas_con_mov_post` en contexto/API).
- Si hay líneas con snapshot ≠ 0, advertencia en español de posible faltante/diferencia al autorizar MSTOCK más adelante.
- **Checkbox obligatorio:** «Entiendo que no hay deshacer en pantalla» — el CTA **Marcar como 0** permanece deshabilitado hasta marcarlo.
- Tras confirmar: POST vacío `{}` → toast de éxito; si la respuesta trae `advertencia`, toast **warning** adicional; reload del analizador.

**Post-marca — recálculo ajuste post-snapshot:** fuera de la transacción de marcado se invoca `recalcular_ajuste_post_snapshot(..., pisar_overrides=False)`. Si el recálculo **falla**, el marcado **ya quedó confirmado** (sin rollback): la API responde `ok: true` con campo `advertencia` en español; la UI muestra warning y un reload posterior recalcula al abrir el analizador.

**API:** `POST /stock/api/campana/<id>/marcar-no-contados-cero/` · permiso `gestionar` · body `{}`.

```jsonc
// 200
{
  "ok": true,
  "lineas_marcadas": 192,
  "lineas_con_snap_ne0": 30,
  "lineas_con_mov_post": 5,
  "mensaje": "192 líneas marcadas con Contado = 0.",
  "advertencia": null  // o string si falló el recalc post-commit
}
```

**Idempotencia:** segunda ejecución sin líneas `IS NULL` → `lineas_marcadas: 0`, sin nuevos eventos ni auditorías.

**Servicio:** `marcar_no_contados_como_cero`, `contar_desglose_no_contados` / `contar_lineas_no_contadas` en `stock/services/inventario_fisico.py`. Constantes: `ACCION_AUDIT_CONTADO_CERO_MASIVO`, `MOTIVO_CONTADO_CERO_SUPERVISOR`.

**Corrección operativa (sin botón revertir en v1):** revertir manualmente en MySQL acotando por auditoría `contado_cero_masivo` (patrón validado en corrida manual campaña 3):

```sql
-- 1) Identificar líneas de la corrida
SELECT id_linea, id_articulo, id_deposito, created_at
FROM inv_fisico_ajuste_auditoria
WHERE id_campana = :id_campana
  AND accion = 'contado_cero_masivo'
  AND created_at >= :fecha_hora_corrida;  -- acotar por ventana temporal

-- 2) UUID de eventos supervisor (36 chars) de la misma corrida
SELECT client_event_id
FROM inv_fisico_evento
WHERE id_campana = :id_campana
  AND motivo = 'Supervisor: no encontrado / contado 0'
  AND client_ts >= :fecha_hora_corrida;

-- 3) Rollback transaccional (solo líneas que siguen en cantidad_contada = 0)
START TRANSACTION;
UPDATE inv_fisico_linea
SET cantidad_contada = NULL,
    diferencia = NULL,
    id_contador = NULL,
    estado_linea = 'Pendiente',
    diferencia_real = NULL
WHERE id_campana = :id_campana
  AND cantidad_contada = 0
  AND id_linea IN (:ids_desde_auditoria);
DELETE FROM inv_fisico_evento
WHERE id_campana = :id_campana
  AND client_event_id IN (:uuids_desde_paso_2);
DELETE FROM inv_fisico_ajuste_auditoria
WHERE id_campana = :id_campana
  AND accion = 'contado_cero_masivo'
  AND id_linea IN (:ids_desde_auditoria);
COMMIT;
-- 4) Recalcular ajustes post-snapshot desde el analizador o vía servicio
```

Ejemplo concreto de corrida campaña 3: `tmp_exports/rollback_campana3_contado_cero_20260807_092218.sql`.

### Offline (PWA)

- IndexedDB `synap_inv_fisico` (`theme/static/js/inv_fisico_offline.js`): stores `catalogo`, `cola`, `meta`.
- Prefetch 1× por campaña/depósito; cola local con `client_event_id` UUID.
- Sync: `POST /stock/api/conteo/sync/` → `{aceptados, conflictos, rechazados}`.
- Whitelist Nivel A: `core/middleware/mobile_level_a_middleware.py`, `core/pwa_nivel_a.py`, precache en `theme/static/sw.js`.

### Escáner y búsqueda manual (conteo móvil)

- **Cámara / escáner:** `getUserMedia` exige **contexto seguro** (HTTPS o `localhost`). En HTTP por IP (ej. `http://181.x.x.x:8100`) el botón «Escanear» muestra un aviso en español y enfoca el ingreso manual; no hay acceso a la cámara.
- **Cantidad tras selección:** al escanear, seleccionar desde el ingreso manual o reabrir un conteo, Synap espera el cierre de la cámara y enfoca automáticamente **Cantidad**. El campo usa el teclado numérico del sistema cuando el navegador lo permite y, en móvil, muestra además un teclado numérico en pantalla (0–9, borrar y limpiar) para cargar sin tocar el input.
- **Ingreso manual:** botón «Ingreso manual» abre un modal con búsqueda **predictiva** (debounce ~250 ms) sobre IndexedDB (`InvFisicoOffline.buscarPorEanONombre`, máx. ~40 sugerencias): coincidencia exacta por EAN o contiene en nombre. **No** busca por código manual ni ID de sistema. En desktop el modal es más ancho (`sm:max-w-xl` … `lg:max-w-3xl`). Flecha abajo/arriba navega la lista; Enter confirma la sugerencia resaltada (o EAN exacto / primer hit). Click en sugerencia también selecciona. Sin campo de búsqueda en la pantalla principal.
- **Corregir conteo:** panel **Artículos contados** (siempre visible) lista lo registrado en el depósito: carga desde API `GET /stock/api/conteo/registrados/` + IndexedDB local, con filtro por código/nombre. Tocá un ítem para reabrir y corregir (modal de confirmación). Re-escanear o rebuscar el mismo artículo también precompleta la cantidad anterior. El mismo operario puede sobrescribir en sync (`evaluar_resultado_evento_sync`); al encolar una corrección se reemplaza el evento pendiente previo del mismo artículo/depósito.
- Si la cámara falla (HTTPS, permisos, sin dispositivo), se abre el modal de ingreso manual.
- Offline: en `init()`, si no hay red, `totalCatalogo` se obtiene con `InvFisicoOffline.contarCatalogo()` del catálogo ya prefetched; la búsqueda no depende de API.
- Si `totalCatalogo === 0` (catálogo no descargado), el modal muestra aviso para conectar y recargar (o sesión con prefetch previo).
- **Cantidad blindada contra el lector (wedge):** el campo **Cantidad** solo acepta dígitos (`sanitizarCantidad`, `maxlength=6`). `validarCantidad` rechaza valores con largo típico de código de barras (**8, 12, 13 o 14 dígitos**) y cualquier cifra de más de **6 dígitos**, con mensaje en español. Además, tras `onScan` / `seleccionarArticulo` hay un **bloqueo de ~400 ms** (`bloquearWedgeCantidad`): durante esa ventana `onKeydownCantidad` descarta las teclas del lector y el Enter final, y solo se admite el **pad numérico en pantalla**. Esto evita el bug de registrar el EAN como cantidad.

### Shell PWA mobile (operario)

Las pantallas de conteo tienen **templates mobile dedicados** seleccionados por `get_template_for_device` (`request.is_mobile`), con la convención `stock/conteo/X.html` → `stock/conteo/mobile/X.html`:

| Ruta | Desktop | Mobile |
|------|---------|--------|
| `/stock/conteo/` | `stock/conteo/mis_conteos.html` | `stock/conteo/mobile/mis_conteos.html` |
| `/stock/conteo/<id>/` | `stock/conteo/conteo.html` | `stock/conteo/mobile/conteo.html` |

- **Chrome Synap visible:** igual que `mpr/templates/mpr/mobile/parte_operario.html`, el navbar fijo (hamburguesa, logo y perfil) y la barra de estado permanecen visibles. `stock/conteo/includes/_pwa_shell.html` no altera sus reglas ni el padding vertical que `base_app.html` reserva para ellos. Se activa con `document.body.classList.add('conteo-pwa')` al inicio del bloque `content`.
- **Fullscreen útil dentro del shell:** `{% block extra_meta %}` agrega `viewport-fit=cover`; el contenedor `.conteo-pwa-root` usa `height: calc(100dvh - 3.5rem - 2rem)` para reservar navbar y barra de estado, además de `env(safe-area-inset-left/right)`. Layout de tres zonas: header interno compacto, cuerpo scrolleable (`.conteo-pwa-scroll`) y zona de acciones inferior. Sheets y modales móviles reservan `bottom-8` para no quedar debajo de la barra de estado.
- **Targets táctiles:** botones, enlaces e inputs con `min-height: 2.75rem` (teclas del pad, `3rem`); inputs a `16px` para evitar el zoom automático de iOS.
- **Layout de conteo:** header (volver a «Mis conteos», campaña, depósito, chip En línea/Offline) → KPIs en una línea (contados/total, pendientes de sync, botón **Sincronizar**) + barra de avance → CTAs **Escanear** / **Manual** → cámara o artículo seleccionado → **Cantidad + pad numérico + Registrar conteo** siempre visibles cuando hay artículo → barra inferior **Artículos contados (N)** que abre un **sheet** con filtro y listado (cada ítem muestra `Cant. N` explícito y el código aparte). El historial nunca empuja el flujo de escaneo.
- **Mis conteos mobile:** tarjetas grandes por campaña con estado, depósitos y CTA **Contar** a ancho completo; estado vacío explícito.
- **Lógica compartida:** el Alpine `conteoInvFisico()` vive en `stock/conteo/includes/_conteo_alpine.html` y lo incluyen desktop y mobile; no debe duplicarse (test `test_logica_alpine_extraida_a_include_compartido`).

### Seguridad / no-filtración

- APIs contador **no** serializan `saldo_snapshot`, `diferencia` ni campos de ajuste post-snapshot (`ajuste_sistema`, `ajuste_manual`, `ajuste_efectivo`, `disponible_ajustado`, `diferencia_real`, `saldo_actual_ref`) — lista `CAMPOS_PROHIBIDOS_CONTEO` en `inventario_fisico.py` (tests `test_inv_fisico_no_filtracion.py`).
- Autorización bloqueada si:
  - `pendientes_cliente > 0` (cola IndexedDB reportada por UI), o
  - conflictos `resultado=conflicto` en `inv_fisico_evento`, o
  - campaña ≠ `EnRevision`.

### MSTOCK

Tras autorización (con recálculo fresco de ajustes), por cada grupo (depósito × motivo):

- **Diferencia real** &lt; 0 → motivo **Faltante (3)**, renglón **Salida**.
- **Diferencia real** &gt; 0 → motivo **Sobrante (4)**, renglón **Entrada**.
- **Diferencia real** = 0 → sin movimiento (aunque la diferencia cruda snapshot ≠ 0).

Invoca `administranet_stock.alta_movimiento` con cabecera MSTOCK y renglones normalizados (`administranet_types`). Auditoría por línea en `inv_fisico_ajuste_auditoria` con `accion='autorizacion'` y `codigo_movimiento`.

## Permisos

| Código | Rol |
|--------|-----|
| `stock.inventario_fisico.contar` | Operario móvil |
| `stock.inventario_fisico.gestionar` | Supervisor: campañas, monitor, analizador |
| `stock.inventario_fisico.autorizar` | Aplicar MSTOCK |

Decorador: `@tiene_permiso` en vistas/API.

## Rollback / anulación

| Estado | Acción | MSTOCK |
|--------|--------|--------|
| Borrador / EnConteo / EnRevision | Anular (modal Synap) | No |
| EnConteo / EnRevision | Revertir «contado cero masivo» (SQL manual por auditoría; ver sección analizador) | No |
| Autorizado (error parcial) | Revisión manual | Según trazas |
| Aplicado | Compensación manual | Fuera de MVP automatizado |

Rollback despliegue: deshabilitar URLs/permisos; quitar whitelist PWA; DDL no destructivo (tablas pueden quedar vacías).

## Tests

```bash
docker exec Synap_app python manage.py test stock.tests.test_inv_fisico_*
```

Módulos: `catalog`, `campana`, `sync`, `no_filtracion`, `middleware`, `mobile`, `offline_static`, `ajuste`, `ajuste_post_snapshot`, `urls`, `permisos`.

## Checklist verificación MVP (manual)

### Conteo móvil

- [ ] Operario con permiso `contar` abre `/stock/conteo/` en móvil Nivel A.
- [ ] Prefetch catálogo ciego (sin saldo/diferencia visible).
- [ ] Scan EAN (HTTPS/localhost) o ingreso manual por EAN/nombre → cantidad en **&lt; 8 s** con catálogo ya prefetched; el foco pasa a Cantidad y aparece el teclado numérico en pantalla.
- [ ] En HTTP por IP: aviso de cámara no disponible; ingreso manual funciona con catálogo cargado.
- [ ] En móvil: navbar, perfil y barra de estado Synap permanecen visibles; el layout interno usa todo el alto útil y el pad + «Registrar conteo» quedan visibles sin scroll.
- [ ] Escanear con lector wedge: la cantidad **no** se completa con el EAN; si se pega un código de barras, aparece el aviso «parece un código de barras».
- [ ] Barra inferior «Artículos contados (N)» abre el sheet y cada ítem muestra `Cant. N`.
- [ ] Modo offline 30+ min: conteos en cola local; banner «N pendientes».
- [ ] Al reconectar: sync completo o conflictos explícitos en español (no pérdida silenciosa).

### Supervisor escritorio

- [ ] Crear campaña en depósitos MPR elegibles; snapshot de líneas.
- [ ] Asignar contadores; abrir conteo (`EnConteo`).
- [ ] Monitor muestra progreso y conflictos sync.
- [ ] Cerrar conteo → `EnRevision`.
- [ ] Analizador: filtros faltante/sobrante; multi-marca (GET `marcas_incluidos`); búsqueda en vivo por código/nombre; columnas **Disponible**, **Cargado después**, **Disponible ajustado**, **Diferencia real**, **Contador**; botón actualizar ajustes; detalle línea con movimientos post-snapshot en ≤ 2 clics desde monitor.
- [ ] Autorizar bloqueado si hay `pendientes_cliente` o conflictos sync.
- [ ] Autorizar OK → campaña `Aplicado`, MSTOCK Faltante/Sobrante según **diferencia real**, línea diff_real=0 sin movimiento.
- [ ] Anular en `EnConteo` → `Anulado` sin MSTOCK.

### Separación consulta pivote

- [ ] Menú distingue «Inventario físico» vs «Consulta inventario».
- [ ] `/stock/inventario/` sigue siendo tabla pivote MPR (sin regresión).

## Referencias

- Change SDD: `openspec/changes/stock-inventario-fisico/`
- Design/spec ajuste: `specs/stock-inventario-fisico-ajuste/spec.md`
- UI canon: `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`
- Tipos AdministraNET: `docs/general/TIPOS_DATOS_ADMINISTRANET.md`
