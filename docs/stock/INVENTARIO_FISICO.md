# Inventario físico Synap (conteo ciego)

Módulo de **inventario físico / conteo ciego** migrado desde `Inventario.frm` (VB6). Distinto de la **consulta pivote MPR** en [`/stock/inventario/`](INVENTARIO_TABLA_MPR.md) (`stock-inventario-tabla`).

## Alcance MVP

- Campañas mensuales en depósitos MPR (`Terminado`, `2daSeleccion`).
- Solo artículos con `articulo.tipo_art_fab` en **`Terminado`** o **`Fabricado 2da`** (excluye Fabricado, Tercero y vacíos).
- Conteo ciego offline-first (PWA Nivel A) con sync idempotente.
- Analizador supervisor con diferencia `contado − snapshot` (columna UI **Disponible**, campo interno `saldo_snapshot`).
- Cantidades en UI (disponible, contado, diferencia, eventos) se muestran como **enteros** (sin decimales); el ingreso móvil usa `inputmode="numeric"` y validación JavaScript ≥ 0.
- Autorización explícita y posteo MSTOCK vía `core/services/administranet_stock.py` (Faltante=3 / Sobrante=4).
- **Sin** volcado automático a tablas legacy `inventario*` (fase 2 opcional).

## Arquitectura

### Datos (MySQL empresa)

| Tabla | Rol |
|-------|-----|
| `inv_fisico_campana` | Cabecera: fecha, estado, depósitos JSON, contadores, `id_movimiento_mstock` |
| `inv_fisico_linea` | Proyección artículo×depósito: `saldo_snapshot`, `cantidad_contada`, `diferencia` (privados al contador) |
| `inv_fisico_evento` | Ledger append-only con `client_event_id` UNIQUE (sync idempotente) |

DDL idempotente: `stock/sql/001_inv_fisico_tables.sql` → proveedor `run_stock_inv_fisico_tables_mysql` en `core/services/legacy_mysql_schema/catalog.py`.

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
- `calcular_diferencia(contado, snapshot)` = contado − snapshot.
- `autorizar_y_aplicar_campana`: bloqueo sync → Autorizado → MSTOCK → Aplicado.
- `anular_campana`: Borrador/EnConteo/EnRevision sin MSTOCK.

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

**Analizador (`analizador.html`)** — filtros de diferencia (Todas / Faltante / Sobrante / Con diferencia) vía GET `filtro`; multi-marca con tags (`marcas_incluidos`, catálogo `listar_marcas_catalogo`, artículo `CodigoMarca`); botón **Aplicar filtros** envía GET preservando `filtro`. Búsqueda **Buscar en tabla** filtra en vivo (Alpine) por código y nombre sobre filas ya cargadas. Columna de saldo al abrir conteo: **Disponible** (campo interno `saldo_snapshot`).

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

### Seguridad / no-filtración

- APIs contador **no** serializan `saldo_snapshot` ni `diferencia` (tests `test_inv_fisico_no_filtracion.py`).
- Autorización bloqueada si:
  - `pendientes_cliente > 0` (cola IndexedDB reportada por UI), o
  - conflictos `resultado=conflicto` en `inv_fisico_evento`, o
  - campaña ≠ `EnRevision`.

### MSTOCK

Tras autorización, por cada grupo (depósito × motivo):

- Diferencia &lt; 0 → motivo **Faltante (3)**, renglón **Salida**.
- Diferencia &gt; 0 → motivo **Sobrante (4)**, renglón **Entrada**.
- Diferencia = 0 → sin movimiento.

Invoca `administranet_stock.alta_movimiento` con cabecera MSTOCK y renglones normalizados (`administranet_types`).

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
| Autorizado (error parcial) | Revisión manual | Según trazas |
| Aplicado | Compensación manual | Fuera de MVP automatizado |

Rollback despliegue: deshabilitar URLs/permisos; quitar whitelist PWA; DDL no destructivo (tablas pueden quedar vacías).

## Tests

```bash
docker exec Synap_app python manage.py test stock.tests.test_inv_fisico_*
```

Módulos: `catalog`, `campana`, `sync`, `no_filtracion`, `middleware`, `mobile`, `offline_static`, `ajuste`, `urls`, `permisos`.

## Checklist verificación MVP (manual)

### Conteo móvil

- [ ] Operario con permiso `contar` abre `/stock/conteo/` en móvil Nivel A.
- [ ] Prefetch catálogo ciego (sin saldo/diferencia visible).
- [ ] Scan EAN (HTTPS/localhost) o ingreso manual por EAN/nombre → cantidad en **&lt; 8 s** con catálogo ya prefetched; el foco pasa a Cantidad y aparece el teclado numérico en pantalla.
- [ ] En HTTP por IP: aviso de cámara no disponible; ingreso manual funciona con catálogo cargado.
- [ ] Modo offline 30+ min: conteos en cola local; banner «N pendientes».
- [ ] Al reconectar: sync completo o conflictos explícitos en español (no pérdida silenciosa).

### Supervisor escritorio

- [ ] Crear campaña en depósitos MPR elegibles; snapshot de líneas.
- [ ] Asignar contadores; abrir conteo (`EnConteo`).
- [ ] Monitor muestra progreso y conflictos sync.
- [ ] Cerrar conteo → `EnRevision`.
- [ ] Analizador: filtros faltante/sobrante; multi-marca (GET `marcas_incluidos`); búsqueda en vivo por código/nombre; columna **Disponible**; detalle línea en ≤ 2 clics desde monitor.
- [ ] Autorizar bloqueado si hay `pendientes_cliente` o conflictos sync.
- [ ] Autorizar OK → campaña `Aplicado`, MSTOCK Faltante/Sobrante, línea diff=0 sin movimiento.
- [ ] Anular en `EnConteo` → `Anulado` sin MSTOCK.

### Separación consulta pivote

- [ ] Menú distingue «Inventario físico» vs «Consulta inventario».
- [ ] `/stock/inventario/` sigue siendo tabla pivote MPR (sin regresión).

## Referencias

- Change SDD: `openspec/changes/stock-inventario-fisico/`
- Design/spec ajuste: `specs/stock-inventario-fisico-ajuste/spec.md`
- UI canon: `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`
- Tipos AdministraNET: `docs/general/TIPOS_DATOS_ADMINISTRANET.md`
