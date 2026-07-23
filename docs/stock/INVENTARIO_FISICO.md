# Inventario físico Synap (conteo ciego)

Módulo de **inventario físico / conteo ciego** migrado desde `Inventario.frm` (VB6). Distinto de la **consulta pivote MPR** en [`/stock/inventario/`](INVENTARIO_TABLA_MPR.md) (`stock-inventario-tabla`).

## Alcance MVP

- Campañas mensuales en depósitos MPR (`Terminado`, `SemiElaborado`, `2daSeleccion`).
- Conteo ciego offline-first (PWA Nivel A) con sync idempotente.
- Analizador supervisor con diferencia `contado − snapshot`.
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

- Campañas, snapshot desde `stock_deposito.saldo`, sync batch, analizador.
- `calcular_diferencia(contado, snapshot)` = contado − snapshot.
- `autorizar_y_aplicar_campana`: bloqueo sync → Autorizado → MSTOCK → Aplicado.
- `anular_campana`: Borrador/EnConteo/EnRevision sin MSTOCK.

### Rutas

| Ruta | Permiso | Descripción |
|------|---------|-------------|
| `/stock/inventario-fisico/` | `stock.inventario_fisico.gestionar` | Listado campañas |
| `/stock/inventario-fisico/nueva/` | gestionar | Alta campaña + snapshot |
| `/stock/inventario-fisico/<id>/monitor/` | gestionar | Progreso, conflictos, cierre conteo |
| `/stock/inventario-fisico/<id>/analizador/` | gestionar | Diferencias, filtros faltante/sobrante |
| `/stock/inventario-fisico/<id>/linea/<id_linea>/` | gestionar | Detalle eventos por línea |
| `/stock/conteo/` | `stock.inventario_fisico.contar` | PWA operario |
| `/stock/api/conteo/prefetch/` | contar | Catálogo ciego |
| `/stock/api/conteo/sync/` | contar | Sync batch |
| `/stock/api/campana/<id>/autorizar/` | `stock.inventario_fisico.autorizar` | Autorizar + MSTOCK |

### Offline (PWA)

- IndexedDB `synap_inv_fisico` (`theme/static/js/inv_fisico_offline.js`): stores `catalogo`, `cola`, `meta`.
- Prefetch 1× por campaña/depósito; cola local con `client_event_id` UUID.
- Sync: `POST /stock/api/conteo/sync/` → `{aceptados, conflictos, rechazados}`.
- Whitelist Nivel A: `core/middleware/mobile_level_a_middleware.py`, `core/pwa_nivel_a.py`, precache en `theme/static/sw.js`.

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
- [ ] Scan EAN → cantidad en **&lt; 8 s** con catálogo ya prefetched.
- [ ] Modo offline 30+ min: conteos en cola local; banner «N pendientes».
- [ ] Al reconectar: sync completo o conflictos explícitos en español (no pérdida silenciosa).

### Supervisor escritorio

- [ ] Crear campaña en depósitos MPR elegibles; snapshot de líneas.
- [ ] Asignar contadores; abrir conteo (`EnConteo`).
- [ ] Monitor muestra progreso y conflictos sync.
- [ ] Cerrar conteo → `EnRevision`.
- [ ] Analizador: filtros faltante/sobrante; detalle línea en ≤ 2 clics desde monitor.
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
