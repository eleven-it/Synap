# Módulo Migración BEST → Synap MPR

**Fecha:** 10/07/2026  
**Ubicación UI:** Producción (MPR) → Configuración → **Migración BEST** (`/mpr/migracion-best/`)  
**Código:** `mpr/best_migration/`

## Objetivo

Resolver la **paridad de maestros** antes de sembrar pedidos abiertos BEST como PED MPR. La migración de pedidos queda **bloqueada** hasta completar los dominios obligatorios.

**Alcance del gate (cutover):** cuentan filas con `requerido_migracion=True` en **pedidos abiertos** BEST (`REP_ORDENES_COMBINADO` con `Finalizada=0` y `Pendiente>0`): artículos y clientes de esas órdenes. Los SKUs con saldo en depósito (`REP_INVENTARIOS`, `STOCK_DEPOSITO`) se sincronizan para stock inicial coherente pero **no bloquean** el gate de pedidos. El resto es histórico y no bloquea.

## Categorías de migración (UI)

| Categoría | Condición | Bloquea gate |
|-----------|-----------|--------------|
| **Cumple** | `requerido_migracion=True` + VALIDADO con IDArt/Código | No (resuelto) |
| **Necesario pendiente** | `requerido_migracion=True` + sin resolver | **Sí** |
| **Histórico / no necesario** | `requerido_migracion=False` | No |
| **Excluido** | estado DESCARTADO (requerido o no) | No (cuenta resuelto si era requerido) |

Propiedad de modelo: `categoria_migracion` → `CUMPLE` \| `NECESARIO_PENDIENTE` \| `NO_NECESARIO` \| `EXCLUIDO`.

Campos de alcance en `BestArticuloMap` / `BestClienteMap`:

- `requerido_migracion` (bool, indexado)
- `en_snapshot_abierto` (bool, indexado)
- `origen_requerimiento`: `PEDIDO_ABIERTO` \| `STOCK_DEPOSITO` \| `BOM_FABRICADO` \| `HISTORICO`

**Guard `BOM_FABRICADO`:** las filas con origen `BOM_FABRICADO` **nunca** entran en `refresh_parity_counters` / `migracion_habilitada` ni se borran en `recalcular_mapeo_articulos`.

Al recalcular/sincronizar: SKUs o clientes fuera del snapshot abierto pero ya VALIDADO/DESCARTADO pasan a `requerido_migracion=False` y `origen_requerimiento=HISTORICO` (no se borran).

**Staging en Postgres (no MySQL):** los mapas y el gate viven en tablas Synap `mpr_best_*_map` / `mpr_best_migration_parity`. Un restore de AdministraNET **no** limpia esta paridad. Para reiniciar:

- **UI:** hub `/mpr/migracion-best/` → botón **Reiniciar migración** (modal con riesgos + checkbox + Cancelar / Confirmar).
- **CLI:**

```bash
docker exec Synap_app python manage.py reiniciar_migracion_best --base-empresa=administranet1
docker exec Synap_app python manage.py reiniciar_migracion_best --base-empresa=administranet1 --ejecutar
```

Luego en `/mpr/migracion-best/`: recalcular artículos → sincronizar clientes/depósitos/stock → confirmar unidades.

**Importante:** el reinicio **no deshace** MSTOCK/PED/`stock_reserva` ya escritos en MySQL.
## Flujo

1. **Hub** — checklist de dominios + gate.
2. **Artículos terminados** — recalcular inferencia 1:1 desde pedidos abiertos; universo Admin `tipo_art_fab=Terminado`. Los fabricados (BOM) viven en dominio aparte.
3. **Clientes** — sincronizar + inferir; misma semántica de alcance y filtros.
4. **Unidades** — confirmar que BEST → `stockp.cantidad` se interpreta en **pares**.
5. **Pedidos (gate)** — se habilita solo con artículos + clientes **requeridos** resueltos y unidades OK. Siembra PED vía `migrar_pedidos_best` (ensayo/confirmar).

Contadores de gate en `BestMigrationParity`: `articulos_total` / `articulos_resueltos` (y clientes) cuentan **solo** `requerido_migracion=True`.

## Dominios

| Dominio | Obligatorio para pedidos | Estado módulo |
|---------|--------------------------|---------------|
| Artículos terminados | Sí | Implementado (inferencia + validación UI + lote score + selección múltiple) |
| Artículos fabricados | No | Implementado (BOM Admin → matcher Admin→BEST directo; no bloquea gate PED) |
| Clientes | Sí | Implementado (inferencia CUIT/nombre/campaña + validación UI + lote + selección múltiple) |
| Unidades (par) | Sí | Confirmación manual en hub |
| Depósitos / etapas | No | Implementado (REP_INVENTARIOS + inferencia tipo_mpr) |
| Stock inicial | No | Implementado (opening balance + dry-run) |
| Stock de seguridad (reserva) | No | Implementado (`MC.MCSS` → `articulo.stock_reserva`) |
| Operarios | No | Implementado (diccionario TTNOTE ↔ sue_abm_empleado) |

## Modelos (PostgreSQL Synap — no toca MySQL/Azure)

- `mpr_best_articulo_map`
- `mpr_best_cliente_map`
- `mpr_best_deposito_map`
- `mpr_best_stock_inicial_map`
- `mpr_best_migration_parity`

Contadores opcionales en paridad: `depositos_total/resueltos`, `stock_inicial_total/resueltos`.  
`depositos_ok` y `stock_inicial_ok` se calculan en `refresh_gate` pero **no** bloquean `migracion_habilitada`.

## Artículos (maestro 1:1)

Fuentes BEST:

- **Pedidos abiertos:** `REP_ORDENES_COMBINADO` (`Finalizada=0`, `Pendiente>0`) — `recalcular_mapeo_articulos`. Origen `PEDIDO_ABIERTO`. **Solo estos bloquean el gate** de migración de pedidos.
- **Saldos en depósito:** `REP_INVENTARIOS` (`Stock ≠ 0`) — `asegurar_articulos_desde_inventario`. Origen `STOCK_DEPOSITO`. Opcionales para el cutover de PED; útiles para stock inicial coherente.

`refresh_parity_counters` cuenta `articulos_total` / `articulos_resueltos` **solo** con `origen_requerimiento=PEDIDO_ABIERTO`.

UI (`/mpr/migracion-best/articulos/`):

- Badges: **Necesario pedido** / **Necesario stock** / Cumple pedido / Cumple stock.
- Cola default: solo pendientes de pedido. Checkbox **Incluir stock en depósito** para ver/mapear stock.
- «Aceptar inferidos altos» aplica solo a pedidos abiertos.
- **Dar de alta en Admin** (fila o selección) para `SIN_CANDIDATO` / `SIN_MATCH` sin candidato:
  - Servicio `core.services.administranet_articulo.crear_articulo` (paridad mínima CargaArticulo).
  - `id_manual` = MMID BEST, `NombreArticulo` = descripción BEST, `CodArtProv` = variante/código BEST.
  - `Precio1V`…`5V` desde `MC.MCSTDC` (CC 3000) o `REP_INVENTARIOS.Precio` si > 0; `PrecioCosto` = 0.
  - `IDSubRubro`, barra CODE128 (`RRRSSSAAAAAA`), `id_unimed=1`, `cantidad_promedio_bulto` desde pack BEST, `CodigoMarca` por diccionario.
  - Rubro/subrubro/IVA desde plantilla Terminado con UM=1; `CodigoArticulo` = MAX+1; `tipo_art_fab=Terminado`.
  - Crea `stock_deposito` saldo 0 en todos los depósitos y valida el mapeo 1:1.

`asegurar_articulos_desde_inventario` infiere mapeo con el mismo matcher. Preserva VALIDADO/DESCARTADO. Si el SKU ya tenía `PEDIDO_ABIERTO`, se conserva; si no, queda `STOCK_DEPOSITO`. El delete de recalcular **no** borra filas `STOCK_DEPOSITO` con `requerido_migracion=True` ni filas `BOM_FABRICADO`.

## Artículos fabricados (BOM Admin, no bloqueante)

- **Fuente BOM:** solo AdministraNET (`en_abm` / `en_abm_formula`). **No** se lee `REP_RECETAS` en BEST.
- **Filas:** cada fila representa un componente Admin `tipo_art_fab=Fabricado` de la BOM, no un producto terminado BEST.
- **Flujo:** terminados `VALIDADO` → explosión primer nivel BOM → componentes `tipo_art_fab=Fabricado` → matcher **Admin→BEST directo** (modelo/tokens/color/talle sobre catálogo 4000/4002; no inversión del matcher de pedidos) → `BestArticuloMap` con `origen_requerimiento=BOM_FABRICADO`, identificado funcionalmente por `admin_idart`.
- **Matcher fabricados:** `match_admin_fabricados_to_best` en `article_matcher.py` puntúa cada SKU BEST del catálogo semi por hit de modelo, Jaccard de tokens, marca, talle y pack suave (componentes 1Par no penalizan fuerte). Color distinto no bloquea: mismo modelo puede inferirse como `INFERIDO_BAJO`/`MEDIO`. Umbral mínimo ~40. Alternativas en `extras.cand_best` para el resolver cuando el top está ocupado por `PEDIDO_ABIERTO`/`STOCK_DEPOSITO`.
- **Catálogo BEST aproximado:** solo `REP_INVENTARIOS` en depósitos **4000 Producción** y **4002 Semi-Embalado**. Se excluyen depósito **4003 Terminado** y pedidos abiertos, porque corresponden a productos terminados.
- **Clave sin SKU:** si no hay coincidencia segura, o el SKU ya pertenece a un mapeo no BOM (`PEDIDO_ABIERTO`, `STOCK_DEPOSITO` o `HISTORICO`), la fila usa `FAB:{IDArt}` y queda `SIN_CANDIDATO`; la UI muestra «Sin sugerencia BEST».
- **Persistencia:** `admin_idart` = componente Admin (fijo desde BOM); `best_id_articulo` = MMID BEST del componente (inferido o asignado manualmente). La clave temporal `FAB:{IDArt}` se reemplaza al validar/asignar un SKU real vía `asignar_best_a_fabricado`.
- **UI:** `/mpr/migracion-best/articulos-fabricados/` — columnas: Componente Admin (solo lectura), Alcance, Sugerencia BEST (link ámbar `aceptar` si hay MMID real), Acciones (buscador SKU BEST + Asignar/Descartar). API `GET /mpr/migracion-best/api/skus-componentes/?q=` consulta Azure de forma acotada con `TOP`/`LIKE` sobre inventario 4000/4002. Un SKU ocupado por una fila de terminados, stock o histórico **no validada** aparece como reclamable y requiere confirmación explícita para borrar ese mapeo y reasignarlo; nunca se reclama si está `VALIDADO`/`validado=True` ni a otro `BOM_FABRICADO`. **No** hay alta en Admin ni columna «Coincidencia Admin».
- **Limitación vigente:** `REP_RECETAS` aún no se lee. La relación esperada PT → PP → crudo está documentada, pero este catálogo semi es una aproximación hasta incorporar esas recetas.
- **Gate:** dominio `articulos_fabricados` con `obligatorio_para_pedidos=False`; pendientes de fabricados no bloquean cutover ni siembra PED.
- **Stock Semi opcional:** `sincronizar_stock_fabricados_semi` filtra inventario BEST depósito **4002** (Semi-Embalado) y SKUs fabricados validados; misma máquina de olas (`CARGADO` inmutable).

## Clientes (maestro 1:1)

Matcher en `mpr/best_migration/client_matcher.py`: CUIT exacto (100), nombre/id manual exacto, base de campaña (marca + temporada), contención/Jaccard y **tokens significativos compartidos**. Los tokens ≥ 4 caracteres excluyen stopwords (artículos, formas societarias, nombres personales genéricos como JOSE/JUAN/MARIA). Un token compartido (p. ej. `JOSE GERONIMO` → `GERONIMO Deportes`) puntúa ~60 (`AMBIGUO`); varios tokens o fuzzy ortográfico leve (`GRECO`/`GRECCO`, ratio ≥ 0,85 o distancia ≤ 1) suben a 65–72. CUIT exacto sigue siendo `INFERIDO` automático (100).

## Depósitos / etapas

Fuente BEST: `REP_INVENTARIOS` (saldo ≠ 0) y `Deposito Origen` en pedidos abiertos.

Mapeo fijo Id Deposito → `tipo_mpr`:

| Id BEST | Nombre típico | tipo_mpr |
|---------|---------------|----------|
| 4000 | Depósito Producción | Produccion |
| 4002 | Semi-Embalado | SemiElaborado |
| 4003 | Terminado | Terminado |
| 4004 | Sobrante y Segunda | 2daSeleccion |

Al **validar** un depósito se llama `actualizar_deposito_tipo_mpr` si `deposito.tipo_mpr` está vacío o distinto del esperado.

Rutas: `/mpr/migracion-best/depositos/`, sincronizar, validar (aceptar / asignar / descartar / lote score / selección múltiple). Todos los POST de migración BEST usan el modal de espera MPR (`mpr-post-loading`).

En artículos, clientes y depósitos la UI permite marcar filas con checkbox (o «seleccionar todas») y **Aceptar seleccionados (N)** (`accion=aceptar_seleccion`, `POST.getlist("sel")`). Solo aparecen checkboxes en filas no validadas/descartadas que ya tienen candidato Admin. En artículos, el **candidato principal** y las alternativas son links de `accion=asignar` (mismo POST; no hay botón «Aceptar inferido» por fila). La columna **Estado** no se muestra en la grilla (el filtro por estado y los badges del resumen siguen disponibles). Tampoco se muestra **Attrs** (colores/talle/pack/score van en el candidato). Los candidatos principal y Alt/Alt 2 usan el mismo tamaño de texto. Filas **VALIDADO** / **DESCARTADO** tienen **Cambiar mapeo** (`accion=reabrir`): vuelve el SKU a `AMBIGUO` (o `SIN_CANDIDATO` sin IDArt), conserva el candidato/alts y permite reasignar sin reiniciar la migración.

## Stock inicial

Fuente: `REP_INVENTARIOS` agrupado por `[Id Articulo], [Id Deposito]` con `SUM(Stock)` en **pares** (no docenas×12).

Antes de armar líneas, `sincronizar_stock_inicial` llama `asegurar_articulos_desde_inventario` para poblar `BestArticuloMap` con los ~1471 SKUs con saldo (evita masivo `SIN_MAPEO_ARTICULO`).

Requiere `BestArticuloMap` y `BestDepositoMap` en estado VALIDADO. Estados de línea:

- `SIN_MAPEO_ARTICULO` / `SIN_MAPEO_DEPOSITO` — falta maestro
- `LISTO` — ambos mapeados, pendiente conciliación
- `CONCILIADO` — revisado manualmente
- `CARGADO` — movimiento MSTOCK «Stock Inicial» grabado (o sin movimiento si Admin ≥ BEST)

**Carga:** `cargar_stock_inicial_best(dry_run=True)` por defecto. La UI ofrece «Ensayo de carga» y «Confirmar carga» (`confirmar=1`).

La confirmación **no** hace upsert directo a `stock_deposito`: llama a `core.services.administranet_stock.alta_movimiento` con **motivo 1 = Stock Inicial** (misma lógica que `/stock/ingreso-movimiento/`), agrupando por depósito (lotes de hasta 100 renglones). Cada renglón es entrada (`ES=E`) por el **delta** `BEST − saldo Admin`. Antes de grabar, el cargador obtiene `CodigoArticuloT` y `NombreArticulo` desde `articulo` por `IDArt`; `alta_movimiento` vuelve a canonizarlos dentro de su transacción, por lo que `stock.CodigoArticulo` siempre replica el código maestro aunque otro llamador entregue un valor erróneo. Además completa `Cantidad`, `PrecioCostoxU`, `PrecioCostoxR`, `CodSucursal`, `id_manual`, `TipoIVA` y `Alicuota` desde el renglón enriquecido y la cabecera: el costo, IVA e identificador manual provienen de `articulo` solo cuando el renglón no los aporta. Actualiza `movimiento_stock` + `stock` + `stock_deposito` en una transacción MySQL. El `detalle` del movimiento usa solo ASCII (`Cutover BEST -> stock inicial…`): el cliente MySQL legacy (charmap/cp1252) no acepta el carácter `→`.

Las altas de stock inicial envían `id_ref_movstock=1` («Sin Referencia») y completan `stock.CodLaboratorio` desde `articulo`, con valor `1` si el maestro no lo define.

### Stock inicial por olas

La carga MSTOCK puede ejecutarse en **varias olas** (cutover y post-cutover):

| Momento | Qué se procesa |
|---------|----------------|
| **Cutover (ola 1)** | Todas las líneas LISTO/CONCILIADO mapeadas con delta>0 |
| **Post-cutover (ola 2+)** | Solo líneas nuevas que pasaron a LISTO/CONCILIADO tras mapear artículos/depósitos adicionales |

**Ejemplo:** 100 SKUs con saldo BEST al cutover → confirmar carga mueve los que tengan delta>0. Semanas después aparecen 50 SKUs nuevos mapeados → **Sincronizar** + **Confirmar carga** procesa solo esos 50; los 100 ya **CARGADO** no vuelven a ser candidatos.

**Guardrails en `cargar_stock_inicial_best`:**

1. **Sync previo:** antes de ensayo o confirmación llama `sincronizar_stock_inicial` (refresca líneas desde `REP_INVENTARIOS`).
2. **Saldo live:** recalcula delta con `_load_admin_stock_deposito` (MySQL `stock_deposito`), no confía solo en `admin_saldo_actual` del snapshot Postgres.
3. **CARGADO inmutable:** `sincronizar_stock_inicial` no cambia estado ni campos de filas **CARGADO** / **DESCARTADO** (rama preservados); la carga solo considera LISTO/CONCILIADO.
4. **Reconfirmación segura:** si Admin ya alcanzó BEST (delta ≤ 0), marca CARGADO sin `alta_movimiento`.
5. **Sin reinicio:** tras MSTOCK no usar «Reiniciar migración» para olas siguientes; el reinicio no deshace MySQL.

Rutas: `/mpr/migracion-best/stock-inicial/`, sincronizar, validar, cargar.

**Colas UI (pestañas):**

| Cola | Estados | Uso |
|------|---------|-----|
| Pendiente mapeo | `SIN_MAPEO_ARTICULO`, `SIN_MAPEO_DEPOSITO` | Maestros faltantes |
| Listos para carga | `LISTO`, `CONCILIADO` | Ola actual — confirmar carga |
| Ya cargados | `CARGADO` | Solo consulta; no reprocesar |

Copy en pantalla: el stock **crítico al cutover** es Terminados (dep. Terminado); fabricados/Semi-Embalado es opcional post-cutover.

## Asignación manual (UI)

En artículos y clientes, la acción **Asignar** usa búsqueda predictiva Alpine (`mpr/static/mpr/js/best_asignar_maestro.js`):

| Dominio | API | Campo POST |
|---------|-----|------------|
| Artículos | `GET /core/api/articulos/search/?tipo_art_fab=Terminado` (`core_api:articulo_search`) | `admin_idart` |
| Clientes | `GET /core/api/clientes/search/` (`core_api:cliente_search`) | `admin_codigo` |
| Depósitos | `GET /core/api/depositos/search/` (`core_api:deposito_search`) | `admin_cod_deposito` |

Las rutas `*/api/*` no pasan por el chequeo de permiso de módulo del path (p. ej. un usuario MPR sin módulo Core puede buscar artículos Terminado). La vista sigue exigiendo sesión con `base_empresa`.

Depósitos, stock inicial y operarios reutilizan `bestAsignarMaestro` / `bestAsignarDeposito` / `bestAsignarOperario` (`mpr:api_empleados`).

## Operarios / tejedores

**Ruta:** `/mpr/migracion-best/operarios/`  
Rutas: sincronizar, validar (aceptar / asignar / descartar / lote / selección / reabrir).  
**Modelo:** `BestOperarioMap` (`mpr_best_operario_map`).  
Sincroniza letras/códigos desde BEST (`REP_MOVIMIENTOS_TOTAL.Tejedor` o `TT.TTNOTE`; fallback catálogo documentado). Infere contra `sue_abm_empleado`. Validar / asignar / descartar / reabrir. `parity.operarios_ok` cuando todos los requeridos están resueltos. No bloquea el gate de PED.

## Conexión BEST

Variables de entorno (obligatorias para conectar): `BEST_AZURE_SERVER`, `BEST_AZURE_DATABASE`, `BEST_AZURE_USER`, `BEST_AZURE_PASSWORD`, `BEST_AZURE_PORT`. En `.env` de Docker Compose escapar `$` del usuario con `$$` (ej. `BEST_AZURE_USER=interfase$$bestsox`); si no, Compose avisa `bestsox variable is not set` y deja el user truncado.  
Requiere `pymssql` en el entorno de la app.

## Relación con el cutover

Ver `docs/mpr/PROPUESTA_MIGRACION_PEDIDOS_BEST_A_MPR_CUTOVER.md` y diccionario en `docs/mpr/best/diccionario_mapeo_articulos_best_admin_*.md`.

## Siembra de pedidos (PED)

**Estado:** implementado (v1, 10/07/2026).

Servicio: `mpr/best_migration/pedido_loader.py` → `migrar_pedidos_best(base_empresa, dry_run=True, ...)`.

### Flujo

1. **Extract** (Azure, solo lectura): `REP_ORDENES_COMBINADO` con `Finalizada=0 AND Pendiente>0`.
2. **Map** (PostgreSQL Synap): `BestArticuloMap` / `BestClienteMap` / `BestDepositoMap` en estado VALIDADO.
   - Línea sin artículo mapeado → huérfana (no se inserta).
   - Cliente sin mapeo → se omite el pedido entero.
   - Depósito sin mapeo → `CodDeposito=1`.
3. **Gate:** `--confirmar` exige `BestMigrationParity.migracion_habilitada`; el ensayo (dry-run) corre igual y avisa si el gate está cerrado.
4. **Load** (MySQL): `comp_ped` + `stockp` por pedido; idempotencia `NroComprobante = BEST-<orden_nro>`.
   - Si el PED existe y no está anulado: **upsert** (actualiza cabecera, anula renglones `stockp` previos y reinserta) salvo `estado_pedido_opt IN ('Produccion','Terminado')` → skip con aviso.
   - Campos MPR opcionales: `estado_pedido_opt='Pendiente'`, `tipo_pedido_opt='Fabrica'` si existen en el esquema.
5. **Post** (solo confirmar con escrituras): `actualizar_pedidos_produccion(base_empresa, id_usuario)`.

### UI

Ruta: `/mpr/migracion-best/pedidos/` — botones **Ensayo de siembra** y **Confirmar siembra** (solo con gate abierto). POST → `/mpr/migracion-best/pedidos/migrar/`.

### Comando

```bash
docker exec Synap_app python manage.py migrar_pedidos_best --base-empresa=administranet1 --dry-run
docker exec Synap_app python manage.py migrar_pedidos_best --base-empresa=administranet1 --confirmar --id-usuario=1
```

### Limitaciones v1

- Solo `REP_ORDENES_COMBINADO` (no OO/OOL).

## Stock de seguridad (reserva)

**Estado:** implementado (10/07/2026).

Equivalencia: BEST `MC.MCSS` (pares, centro de costo Terminado `MCCCID=4003`) → `articulo.stock_reserva`. Alimenta demanda por reserva (código 0) y resta armar en tablero PCP.

Servicio: `mpr/best_migration/stock_reserva_loader.py` → `migrar_stock_reserva_best`. Por defecto solo escribe filas con `MCSS>0` (no pisa reservas manuales a cero). Requiere `BestArticuloMap` VALIDADO.

```bash
docker exec Synap_app python manage.py cargar_stock_reserva_best --base-empresa=administranet1 --dry-run
docker exec Synap_app python manage.py cargar_stock_reserva_best --base-empresa=administranet1 --confirmar --id-usuario=1
```

UI: hub Migración BEST → dominio «Stock de seguridad (reserva)» (Ensayo / Confirmar). Tras confirmar con cambios, ejecuta `actualizar_pedidos_produccion`.
- No actualiza `stock_deposito.saldo_pedido_cliente` (demanda MPR vía `actualizar_pedidos_produccion`).
- Precios/IVA simplificados (neto = precio BEST × cantidad; IVA 0 en renglón).
- Depósito por línea: mapeo por nombre VALIDADO o default 1.
- Transacción global por lote de pedidos (un rollback falla todo el lote de confirmación).

Tests: `mpr.best_migration.tests.test_pedido_loader`.
