# Propuesta técnica — Migración de pedidos BEST → Synap MPR (corte «off BEST / on Synap»)

**Fecha:** 08/07/2026
**Autor:** Ingeniería Synap (MPR)
**Estado:** ⛔ **SUSPENDIDA (08/07/2026)** — ver banner de suspensión más abajo.
**Alcance:** Extraer los **pedidos abiertos** del sistema **BEST** (Azure SQL, solo lectura) y sembrarlos como **demanda de producción** en Synap MPR (AdministraNET MySQL), de forma que en el momento del **corte** el Tablero de producción y el flujo OPT/OPP/Armado de Synap reflejen exactamente el trabajo pendiente que hoy gobierna BEST.

---

> ## ⛔ Suspensión (08/07/2026) — actualización 10/07/2026
>
> **Esta migración sigue SUSPENDIDA para go-live completo**, pero el bloqueo de mapeo ya no es total.
>
> **Motivos originales:**
> 1. Los SKU/artículos de Synap no comparten el mismo código que BEST (`MMID` ≠ `id_manual` variante).
> 2. Synap MPR ya opera nativo con PED AdministraNET.
>
> **Avance 10/07/2026 (solo lectura, sin cambios en DBs):**
> - Diccionario talle/color/pack + alias de modelo: `docs/mpr/best/diccionario_mapeo_articulos_best_admin_20260710_1107.md`
> - Equivalencias usables (MATCH_ALTO/MEDIO) sobre SKUs de pedidos abiertos: **171/256 (66,8%)** en `docs/mpr/best/equivalencia_best_idart_usable_20260710_1107.csv`
> - Reporte completo: `docs/mpr/best/mapeo_articulos_best_admin_resumen_20260710_1107.md`
>
> **Para reactivar el corte:** (1) spot-check del CSV usable, (2) resolver cola residual (~85 SKUs SIN_*/AMBIGUO/BAJO; muchos sin variante 2P/3P en Admin o solo 1Par Logo), (3) ejecutar `migrar_pedidos_best` sembrando solo líneas con `IDArt` validado.
>
> **Actualización 10/07/2026 (tarde):** cargador `migrar_pedidos_best` **implementado** (`mpr/best_migration/pedido_loader.py`, comando `manage.py migrar_pedidos_best`, UI en gate `/mpr/migracion-best/pedidos/`). Ver `docs/mpr/MODULO_MIGRACION_BEST_MPR.md` § Siembra de pedidos.

**Documentos que complementa / referencia:**
- `docs/mpr/MODULO_MIGRACION_BEST_MPR.md` (UI de paridad + gate de pedidos)
- `docs/mpr/BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md` (catálogo Excel → MPR, mapeo de etapas)
- `docs/mpr/BEST_SOX_PCP_PRODUCCION_ALINEACION.md` (fórmula PCP, unidad = par)
- `docs/mpr/BEST_SOX_ITERACION1_VALIDACION.md` (conexión BEST, validación numérica)
- `docs/mpr/FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md` (flujo pedido → demanda → OPT)
- `docs/mpr/DIAGNOSTICO_DEMANDA_MPR.md` (cómo se alimenta la demanda MPR)

> **Nota de dominio (crítica):** en Best Sox **1 unidad = 1 par** y **1 docena = 12 pares** (`BEST_SOX_PCP_PRODUCCION_ALINEACION.md` §0). Toda cantidad de pedido migrada se interpreta en **pares**.

---

## 1. Resumen ejecutivo

Hoy la planta Best Sox planifica y controla producción en **BEST** (ERP sobre Azure SQL). Synap MPR es el sistema destino que debe **reemplazar** esa función. Para poder "apagar" BEST y "encender" Synap MPR sin perder el trabajo en curso, el insumo imprescindible son los **pedidos pendientes** (la demanda): sin ellos, el Tablero de producción de Synap muestra "resta a producir = 0" y la planta queda ciega.

La propuesta define:

1. **Qué es un "pedido"** en cada sistema y cuál es su equivalente semántico.
2. **De dónde** se extraen en BEST (tablas/vistas Azure SQL) y **dónde aterrizan** en Synap (tablas AdministraNET MySQL).
3. La **estrategia recomendada**: sembrar los pedidos como **comprobantes PED nativos** (`comp_ped` + `stockp`) para reutilizar sin cambios el pipeline existente de Synap MPR (Actualizar → `lista_produccion_detalle`/`agrupada` → OPT → OPP → Armado).
4. Una **herramienta de migración** (comando `manage.py`) idempotente, con marca de origen, ensayo (dry-run) y conciliación.
5. El **plan de corte** por fases (preparación → ensayo → operación paralela → corte → verificación → contingencia/rollback).
6. **Criterios de aceptación** y conciliación numérica BEST ↔ Synap.

**Recomendación de arquitectura:** aterrizar los pedidos como **PED (`tipo_pedido_opt='Fabrica'`, `estado_pedido_opt='Pendiente'`)** en AdministraNET, no directamente en `lista_produccion_agrupada`. Motivo: el motor de demanda de Synap (`actualizar_pedidos_produccion`) **recalcula** `agrupada`/`detalle` desde PED en cada carga de pantalla; sembrar por debajo de esa capa se sobreescribiría. Ver §6.

---

## 2. Arquitectura actual de ambos sistemas

| Aspecto | BEST (origen) | Synap MPR (destino) |
|--------|----------------|----------------------|
| Motor | Azure SQL Database | AdministraNET **MySQL** (por empresa) + PostgreSQL (ledgers `mpr_*`) |
| Conexión | `m52q7iitok.database.windows.net:1433`, base `BEST`, usuario lectura `interfase$bestsox` (`pymssql`, ver `core/management/commands/export_azure_schema.py`, `analyze_best_processes.py`) | `mpr/db.py::get_connection(base_empresa)` (MySQL legacy compartido con VB6) |
| Permiso | **Solo lectura** (no INSERT/UPDATE/DELETE en BEST) | Lectura/escritura sobre tablas legacy y `mpr_*` |
| Órdenes/pedidos | Tablas **`OO`** (órdenes, ~565k reg.) / **`OOL`** (líneas), vistas `REP_ORDENES_*` | `comp_ped` (PED) + `stockp`; derivado a `lista_produccion_detalle` + `lista_produccion_agrupada` |
| Ledger de movimientos | **`TT`/`TTL`** → vista `REP_MOVIMIENTOS_TOTAL` (~3,8M reg.) | `movimiento_stock` + `cuerpostock_mstock` + `stock`/`stock_deposito`; ledgers `mpr_*` |
| Inventario | `REP_INVENTARIOS` (por depósito, en docenas/pares) | `stock_deposito` por depósito (`tipo_mpr`) |
| Recetas / BOM | `REP_RECETAS` (PT→PP→crudo) | `en_abm` + `en_abm_formula` (articulo.id_en_abm) |
| Tablero PCP | Planilla **PCP Produccion** (`MAX(pedido − stock_PP, 0)`) | `/mpr/tablero-produccion/` (`listar_tablero_por_articulo`) |

**Conclusión de topología:** BEST y AdministraNET son **bases independientes sin réplica automática** (`BEST_SOX_ITERACION1_VALIDACION.md` §7). El corte requiere un **paso de migración explícito**, no una sincronización mágica.

---

## 3. Definición precisa de "pedido" a ambos lados

### 3.1 En BEST
- **Orden de producción / pedido interno**: cabecera en `OO`, líneas en `OOL` (`OOTYPE` distingue tipo; el análisis previo señala `OOTYPE=3`, depósito `4003` para producción). Estados: `Pendiente` / `Parcial` / `Confirmada` / `Finalizada` (visto en `BS Reporte F Rotacion.xlsx`, hojas `Ordenes-*` y `Pedidos`).
- **Snapshot PCP**: las columnas **Pedido (E)** y **Urgente (F)** del PCP son un **pivot cacheado** de esas órdenes por artículo PP; no son la fuente viva (`BEST_SOX_PCP_PRODUCCION_ALINEACION.md` §3). **No se migra el snapshot**, se migran las **órdenes vivas**.

### 3.2 En Synap MPR
- **Pedido = comprobante `PED`** en `comp_ped` (con `tipo_pedido_opt='Fabrica'`, `estado_pedido_opt IN ('Pendiente','Parcial')`, no anulado) + sus líneas en **`stockp`** (por `IDArt`, con cantidad), y el artículo debe ser **`articulo.tipo_art_fab='Terminado'`**.
- **Demanda derivada:** el botón/carga **Actualizar** (`actualizar_pedidos_produccion`) proyecta esos PED a `lista_produccion_detalle` y luego agrega por artículo en `lista_produccion_agrupada.cantidad_pendiente_prod`, que es lo que consume el Tablero y la ventana OPT.

### 3.3 Equivalencia (proceso, no nombres)

| BEST | Synap MPR | Nota |
|------|-----------|------|
| `OO` (cabecera orden Pendiente/Parcial) | `comp_ped` (PED, Fabrica, Pendiente/Parcial) | 1 orden BEST → 1 comprobante PED |
| `OOL` (línea, artículo + cantidad pendiente) | `stockp` (IDArt + cantidad) | 1 línea → 1 fila `stockp` |
| Artículo PP/PT (MM/MYL id) | `articulo.IDArt` (join por **código manual / SKU**) | requiere mapa de identidad (§7) |
| Cantidad pendiente (pares) | `stockp.cantidad` (pares) | unidad = par |
| Marca "Urgente" | (opcional) flag/campo derivado | ver §5.4 y decisión D4 |

---

## 4. Alcance del corte

### 4.1 Dentro de alcance (esta propuesta)
- Migración de **pedidos/órdenes abiertos** (Pendiente + Parcial) de BEST a demanda Synap.
- Herramienta de extracción BEST → carga AdministraNET, idempotente y auditable.
- Conciliación de la **demanda por artículo** (pares y docenas) BEST ↔ Synap.

### 4.2 Prerrequisitos (fuera del corazón, pero bloqueantes — §8)
- **Maestro de artículos** de Best Sox cargado en `articulo` (con `tipo_art_fab='Terminado'`, `id_en_abm`).
- **BOM/recetas** (`en_abm`/`en_abm_formula`) para explosión pack → componente.
- **Depósitos** con `tipo_mpr` y `suma_stock` correctos.
- **Stock inicial (opening balance)** por depósito/etapa cargado en `stock_deposito` (si no, la "resta a producir" será errónea aunque los pedidos estén perfectos).
- **Operarios/tejedores** (diccionario letra BEST ↔ `sue_abm_empleado`) — necesario para reportes por operario, no para la demanda.

### 4.3 Fuera de alcance
- Migración del **histórico** de movimientos/producción de BEST (se resuelve con operación paralela + reportes; ver `BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md`).
- Sincronización **bidireccional** BEST↔Synap (el corte es unidireccional y de una vez).
- Reescritura del snapshot PCP de Excel.

---

## 5. Fuentes BEST y zona de aterrizaje Synap

### 5.1 Extracción en BEST (solo lectura)
Consulta objetivo (a validar contra el esquema real con `export_azure_schema`):

```sql
-- SOLO LECTURA sobre BEST (Azure SQL) — pseudo-consulta a ajustar a OO/OOL reales
SELECT  o.<nro_orden>        AS orden_best,
        o.<fecha_emision>    AS fecha,
        o.<estado>           AS estado,          -- Pendiente / Parcial
        l.<sku_articulo>     AS codigo_articulo, -- clave de mapeo (código manual)
        l.<cantidad_pend>    AS cantidad_pares   -- pendiente en pares
FROM OO o
JOIN OOL l ON l.<fk_orden> = o.<pk_orden>
WHERE o.<estado> IN ('Pendiente','Parcial')
  AND l.<cantidad_pend> > 0;
```

> La forma exacta de `OO`/`OOL`/`REP_ORDENES_*` debe fijarse ejecutando primero `docker exec Synap_app python manage.py export_azure_schema --output docs/mpr/best/azure_schema_ordenes.md` y acotando a las tablas de órdenes. Se prioriza una **vista `REP_ORDENES_*`** si expone el pendiente ya calculado.

### 5.2 Zona de aterrizaje recomendada (Synap / AdministraNET MySQL)
Crear, por cada orden abierta de BEST, un **comprobante PED** de migración:

| Tabla | Rol | Campos clave a poblar |
|-------|-----|------------------------|
| `comp_ped` | Cabecera PED | `TipoComprobante='PED'`, `tipo_pedido_opt='Fabrica'`, `estado_pedido_opt='Pendiente'`, `Anulado='No'`, `Fecha`, `NroComprobante`/`NroCompBusq` (prefijo de origen, p.ej. `BEST-<orden>`), `CodigoMovimiento` (talonario), cliente genérico de migración |
| `stockp` | Línea de pedido | `CodigoMovimiento` (= cabecera), `IDArt` (mapeado), `cantidad` = pares pendientes |

Luego el flujo **nativo** de Synap hace el resto:
`actualizar_pedidos_produccion` → `lista_produccion_detalle` → `lista_produccion_agrupada.cantidad_pendiente_prod` → Tablero / ventana OPT.

### 5.3 Talonario / numeración
El alta de PED debe respetar la lógica de talonario AdministraNET (SELECT `CodigoMovimiento` codigo=1 FOR UPDATE, incremento) descrita en `FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md` §12, o bien usar un **talonario/serie dedicado de migración** para aislar los comprobantes migrados y poder revertirlos.

### 5.4 "Urgente"
BEST marca un subconjunto **Urgente** (PCP col F). En Synap, la "resta urgente" del tablero se define como `MAX(0, dem_ped − stock_proceso)` (`BEST_SOX_PCP_PRODUCCION_ALINEACION.md` §9.2), donde `dem_ped` = demanda de pedido. Si BEST distingue urgentes a nivel orden/línea, hay dos opciones (decisión **D4**): (a) mapear urgentes a PED separados / campo, o (b) no migrar la marca y derivar urgencia por fecha objetivo. Recomendado: **(b)** en el corte y evaluar (a) en iteración posterior.

---

## 6. Estrategia de migración: alternativas

| Opción | Aterrizaje | Ventajas | Desventajas | Veredicto |
|--------|-----------|----------|-------------|-----------|
| **A — PED nativo** ✅ | `comp_ped` + `stockp` | Reutiliza 100% el pipeline (Actualizar, OPT, OPP, armado, trazabilidad). Idempotente vía nro comprobante de origen. Reversible (anular PED). Compatible con VB6 legacy. | Requiere respetar talonario y cliente genérico. | **Recomendada** |
| B — Directo a `lista_produccion_*` | `lista_produccion_detalle`/`agrupada` | Menos tablas. | `actualizar_pedidos_produccion` **recalcula desde PED y borra/ceroa** líneas huérfanas → la siembra se pierde al primer Actualizar. Sin trazabilidad a comprobante. | Descartada |
| C — Demanda por reserva | `articulo.stock_reserva` | Muy simple. | Agregado por artículo, sin desglose por pedido; no representa órdenes discretas. | Solo complemento |

**Decisión de diseño:** Opción **A**. La clave de idempotencia es `comp_ped.NroCompBusq = 'BEST-<orden_best>'` (o `NroComprobante` con prefijo): re-ejecutar la migración **actualiza** cantidades en vez de duplicar.

---

## 7. Mapeo de datos y clave de identidad de artículo

El punto más delicado del corte: **emparejar el artículo de BEST con `articulo.IDArt` de AdministraNET.**

| Dato | BEST | AdministraNET | Regla de match |
|------|------|----------------|----------------|
| Artículo | código MM/MYL (SKU, ej. `SEAT2402BLNE5`) | `articulo.CodigoArticulo` / `articulo.id_manual` | Join exacto por **código manual/SKU normalizado** (trim, upper) |
| Cantidad | pares pendientes | `stockp.cantidad` | entero (par) |
| Fecha | emisión / objetivo | `comp_ped.Fecha` | ISO; UI muestra dd/MM/yyyy |
| Estado | Pendiente/Parcial | `estado_pedido_opt` | fijo `Pendiente` en el corte |

**Entregable obligatorio:** una **tabla/CSV de mapeo `codigo_best → IDArt`** validada al 100% antes del corte. Los artículos sin match se reportan y se resuelven manualmente (no se migran a ciegas). Sin mapeo confiable, la demanda migrada será incorrecta aunque las cantidades sean exactas.

**Normalización de tipos** (regla `.cursorrules`): usar `core.utils.administranet_types` (`to_int_or_none`, `to_date_or_none`, `str_or_default`) al escribir `comp_ped`/`stockp`.

---

## 8. Prerrequisitos técnicos (checklist bloqueante)

1. **`base_empresa` productiva** de Best Sox confirmada (hoy en docs: `administranet93` = tests, `administranet96` = piloto). **Decisión D1.**
2. Tablas MPR core aplicadas en esa base (`apply_mpr_core_tables`, `mpr/sql/`), incl. `mpr_transicion_lote.id_operario`.
3. **Artículos** Best Sox en `articulo` con `tipo_art_fab='Terminado'` e `id_en_abm` (BOM). Verificable con `diagnosticar_demanda_mpr`.
4. **Depósitos** con `tipo_mpr`/`suma_stock` (ver `sql/ALTER_deposito_tipo_mpr.sql`).
5. **Stock inicial** cargado en `stock_deposito` (opening balance desde `REP_INVENTARIOS`). Sin esto, `pendiente = demanda` (sobreestima).
6. `lista_produccion_detalle` sin FK a `comp_ped` en `codigo_movimiento_pedido` (ver `DIAGNOSTICO_DEMANDA_MPR.md`), o migración de esquema aplicada.
7. Driver **`pymssql`** disponible en el contenedor `Synap_app`.

---

## 9. Herramienta de migración (diseño)

**Forma:** comando `manage.py` en la app `mpr` (ejecutado siempre vía `docker exec Synap_app ...`). Migración de esquema (si hubiera columnas nuevas, p.ej. marca de origen) en el **catálogo central** `core/services/legacy_mysql_schema/catalog.py` (regla `.cursorrules`).

```
mpr/management/commands/migrar_pedidos_best.py
```

**Parámetros:**
- `--base-empresa=administranet96` (destino AdministraNET)
- `--estados=Pendiente,Parcial`
- `--fecha-desde / --fecha-hasta` (opcional, acotar órdenes)
- `--mapa-articulos=<ruta csv>` (codigo_best → IDArt)
- `--dry-run` (default): extrae, mapea, **no escribe**; imprime conciliación
- `--confirmar`: ejecuta la carga en transacción
- `--prefijo-origen=BEST` (idempotencia por `NroCompBusq`)

**Pipeline interno:**
1. **Extract (BEST, solo lectura):** conectar por `pymssql` (credenciales por **variable de entorno**, no hardcode — §12), leer órdenes abiertas (`OO`/`OOL` o `REP_ORDENES_*`).
2. **Map:** resolver `codigo_best → IDArt`; separar matcheados / huérfanos.
3. **Validate/Reconcile:** agregar por artículo (pares/docenas), comparar contra PCP/`REP_PCP_ARMADO` como control cruzado.
4. **Load (MySQL, transacción):** upsert de `comp_ped`+`stockp` por `NroCompBusq='BEST-<orden>'` (INSERT nuevo, UPDATE cantidades si ya existe, anular los que ya no vienen).
5. **Post:** ejecutar `actualizar_pedidos_produccion(base_empresa)` para refrescar `detalle`/`agrupada` y dejar el Tablero listo.
6. **Report:** resumen (órdenes leídas, líneas migradas, huérfanos, total pares/docenas por artículo) a stdout y a `docs/mpr/best/` (log del corte).

**Idempotencia y reversibilidad:** re-ejecución no duplica (upsert por origen). Rollback = anular (`Anulado='Si'`) los PED con prefijo `BEST-` + `actualizar_pedidos_produccion` (deja demanda en 0). Si se usó talonario dedicado, el filtrado es trivial.

---

## 10. Plan de corte (fases)

| Fase | Objetivo | Acciones | Salida |
|------|----------|----------|--------|
| **0. Preparación** | Prerrequisitos §8 | Confirmar `base_empresa`; cargar artículos/BOM/depósitos; exportar esquema BEST órdenes; construir mapa de artículos | Mapa validado 100% |
| **1. Ensayo (dry-run)** | Validar extracción+mapeo | `migrar_pedidos_best --dry-run`; revisar huérfanos y totales | Reporte de conciliación #1 |
| **2. Stock inicial** | Opening balance | Cargar `stock_deposito` desde `REP_INVENTARIOS`; validar contra `reporte_mpr_stock` | Inventario conciliado |
| **3. Operación paralela** (opcional, 3–5 días) | Confianza | Cargar pedidos y comparar Tablero Synap vs PCP BEST diariamente | Tolerancia acordada |
| **4. Corte** | Go-live | Congelar altas en BEST → `migrar_pedidos_best --confirmar` → `actualizar_pedidos_produccion` → verificación | BEST en solo consulta |
| **5. Verificación** | Aceptación | §11: demanda por artículo, Tablero, OPT de prueba | Acta de corte |
| **6. Contingencia** | Rollback | Anular PED `BEST-*` y volver a BEST si falla criterio | Plan probado |

**Congelamiento:** durante la Fase 4, no se deben crear/modificar órdenes en BEST (ventana de mantenimiento) para evitar deriva entre el snapshot migrado y la operación.

---

## 11. Validación y criterios de aceptación

Para el corte se acepta cuando:

1. **Cobertura de mapeo:** 100% de las líneas de órdenes abiertas con match a `IDArt` (o excepciones documentadas y aprobadas).
2. **Paridad de demanda por artículo:** para los N artículos con pedido, `SUM(pares)` migrado en Synap (`lista_produccion_agrupada.cantidad_pendiente_prod`) = pendiente de órdenes BEST, dentro de la **tolerancia acordada** (idealmente 0 tras congelamiento).
3. **Paridad en docenas:** `pares/12` coincide con el conteo en docenas de referencia.
4. **Tablero operativo:** `/mpr/tablero-produccion/` muestra "resta a producir" coherente con PCP Produccion para ≥10 SKUs de control (mismo criterio `MAX(demanda − stock_proceso, 0)`).
5. **Flujo end-to-end:** se puede crear una **OPT** desde la demanda migrada, liberar y registrar **OPP** sin errores.
6. **Roles/trazabilidad:** cada PED migrado es identificable por su origen (`BEST-<orden>`).

**Consultas de control** (reutilizables):

```sql
-- Synap: demanda migrada por artículo (MySQL, base destino)
SELECT id_articulo, SUM(cantidad_pendiente_prod) AS pares
FROM lista_produccion_agrupada
WHERE en_proceso_produccion = 'No' AND cantidad_pendiente_prod > 0
GROUP BY id_articulo;
```
```sql
-- BEST: pendiente por artículo (Azure SQL, SOLO LECTURA)
SELECT l.<sku>, SUM(l.<cantidad_pend>) AS pares
FROM OO o JOIN OOL l ON l.<fk> = o.<pk>
WHERE o.<estado> IN ('Pendiente','Parcial')
GROUP BY l.<sku>;
```

### 11.1 Control obligatorio por pedido y artículo

Antes de aceptar el corte, además del total por artículo, comparar el origen
`stockp` con `lista_produccion_detalle` por el par
`(CodigoMovimiento, IDArt)`. Este control detecta pedidos con una misma
referencia de artículo repartida en varias filas `stockp`: el detalle MPR
debe guardar la **suma** de esas filas en una única línea.

```sql
SELECT cp.NroComprobante, o.codigo_movimiento, o.id_articulo,
       o.pares_stockp, COALESCE(d.pares_detalle, 0) AS pares_detalle
FROM (
    SELECT sp.CodigoMovimiento AS codigo_movimiento, sp.IDArt AS id_articulo,
           SUM(COALESCE(sp.Cantidad, sp.cantidad_pendiente, 0)) AS pares_stockp
    FROM stockp sp
    GROUP BY sp.CodigoMovimiento, sp.IDArt
) o
JOIN comp_ped cp ON cp.CodigoMovimiento = o.codigo_movimiento
JOIN articulo a ON a.IDArt = o.id_articulo AND TRIM(a.tipo_art_fab) = 'Terminado'
LEFT JOIN (
    SELECT codigo_movimiento_pedido, id_articulo,
           SUM(cantidad_pedida) AS pares_detalle
    FROM lista_produccion_detalle
    GROUP BY codigo_movimiento_pedido, id_articulo
) d ON d.codigo_movimiento_pedido = o.codigo_movimiento
   AND d.id_articulo = o.id_articulo
WHERE cp.NroComprobante LIKE 'BEST-%'
  AND COALESCE(cp.Anulado, 'No') = 'No'
  AND COALESCE(d.pares_detalle, 0) <> o.pares_stockp;
```

**Criterio bloqueante:** la consulta debe devolver cero filas y la suma de
ambos lados debe ser idéntica. Ejecutarla después de
`migrar_pedidos_best --confirmar` y una segunda vez tras
`actualizar_pedidos_produccion`; conservar ambos resultados en el acta del
corte.

---

## 12. Riesgos y mitigaciones

| # | Riesgo | Impacto | Mitigación |
|---|--------|---------|-----------|
| R1 | **Mapeo de artículo incompleto/ambiguo** (SKU BEST ≠ código AdministraNET) | Demanda errónea | Mapa validado 100% pre-corte; abortar líneas huérfanas; reporte obligatorio |
| R2 | **Stock inicial ausente/incorrecto** | "Resta a producir" inflada | Fase 2 dedicada; conciliar inventario antes de aceptar |
| R3 | **`actualizar_pedidos_produccion` sobreescribe** siembra directa | Demanda desaparece | Usar Opción A (PED nativo), nunca B |
| R4 | **Credenciales BEST hardcodeadas** en comandos actuales (`analyze_best_processes.py`, `export_azure_schema.py`) | Seguridad (con `ENVIRONMENT=production`) | Mover a variables de entorno; no versionar secretos; rotar contraseña |
| R5 | **Deriva por altas en BEST durante el corte** | Descuadre | Ventana de congelamiento; corte único; re-ejecución idempotente |
| R6 | **Duplicación de comprobantes** al reprocesar | Doble demanda | Upsert por `NroCompBusq='BEST-<orden>'`; talonario dedicado |
| R7 | **Base destino equivocada** (93 test vs 96 piloto vs prod) | Datos en base incorrecta | Parámetro `--base-empresa` explícito + confirmación D1 |
| R8 | **Divisor docenas** (pack×2→6, ×3→4) mal aplicado en artículos pack | Conteos en docenas erróneos | Validar `cantidad_promedio_bulto` vs PACK BEST (`BEST_SOX_GAP...` §2) |
| R9 | **Estados Parcial** con fabricado previo | Doble producción | Migrar solo pendiente neto; `actualizar_pedidos_produccion` preserva fabricado parcial |

---

## 13. Entregables

1. `mpr/management/commands/migrar_pedidos_best.py` (extract/map/validate/load, dry-run + confirmar).
2. Mapa `codigo_best → IDArt` (CSV validado) + reporte de huérfanos.
3. Reporte de conciliación de demanda BEST ↔ Synap (por artículo, pares/docenas).
4. Log del corte en `docs/mpr/best/` (fecha, totales, incidencias).
5. Actualización de este documento con el esquema real de `OO`/`OOL`/`REP_ORDENES_*` tras el export.
6. (Si aplica) migración de esquema en `catalog.py` para marca de origen / talonario de migración.

---

## 14. Decisiones abiertas (a confirmar con producto/planta)

| # | Decisión | Opciones | Recomendación |
|---|----------|----------|---------------|
| **D1** | `base_empresa` destino del corte | `administranet93` / `96` / producción nueva | Confirmar la productiva de Best Sox |
| **D2** | Fuente exacta en BEST | `OO`/`OOL` crudas vs vista `REP_ORDENES_*` | Vista si expone pendiente ya calculado |
| **D3** | Aterrizaje | PED nativo (A) vs directo (B) | **A** (PED nativo) |
| **D4** | Marca "Urgente" | migrar vs derivar por fecha | Derivar; evaluar migrar en iteración 2 |
| **D5** | Estilo de corte | big-bang vs operación paralela | Paralelo 3–5 días si el calendario lo permite |
| **D6** | Numeración PED | talonario real vs serie dedicada de migración | Serie dedicada (aísla y facilita rollback) |
| **D7** | Histórico | migrar vs solo reportes/operación paralela | Solo pedidos abiertos ahora (histórico fuera de alcance) |

---

## 15. Próximos pasos inmediatos

1. Confirmar **D1** (base destino) y **D3/D6** (aterrizaje/numeración).
2. Ejecutar `export_azure_schema` acotado a órdenes para fijar `OO`/`OOL`/`REP_ORDENES_*` reales (cerrar D2).
3. Construir y validar el **mapa de artículos** (bloqueante).
4. Implementar `migrar_pedidos_best` con `--dry-run` y correr conciliación #1.

---

## 16. Referencias

- `core/management/commands/export_azure_schema.py`, `analyze_best_processes.py` (conexión BEST)
- `mpr/services.py` → `actualizar_pedidos_produccion`, `listar_ventana_pack`, `crear_opt_multiples_articulos`, `listar_tablero_por_articulo`
- `docs/mpr/BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md`, `BEST_SOX_PCP_PRODUCCION_ALINEACION.md`, `BEST_SOX_ITERACION1_VALIDACION.md`
- `docs/mpr/FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md`, `DIAGNOSTICO_DEMANDA_MPR.md`
- Planillas de referencia: `Best Sox/*.xlsx`
