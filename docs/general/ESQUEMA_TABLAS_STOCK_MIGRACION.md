# Esquema e índices: Módulo Stock (migración VB6 → Synap)

Documento de Fase 0 del plan de migración. Referencia tablas AdministraNET con mismo formato para operación en paralelo.

## 1. Tablas involucradas

| Tabla | Uso en alta de movimiento | Documentación |
|-------|---------------------------|---------------|
| **cuerpostock_mstock** | Temporal por usuario (renglones en edición). Filtro: Codusuario, visualiza='No', CodigoMovimiento=1 | [tablas/cuerpostock_mstock.md](tablas/cuerpostock_mstock.md) |
| **codmov** | Contador global CodigoMovimiento (codigo=1). UPDATE en misma transacción que el alta | [tablas/codmov.md](tablas/codmov.md) |
| **talonarios** | Numeración MSTOCK (TipoComprobante='MSTOCK', id_punto_venta). SELECT FOR UPDATE, actualizar Nro | [tablas/talonarios.md](tablas/talonarios.md) |
| **movimiento_stock** | Cabecera del movimiento (codigo_movimiento, nro_comprobante, motivo, depósitos, id_usuario, id_ref_movstock, etc.) | [tablas/movimiento_stock.md](tablas/movimiento_stock.md) |
| **stock** | Un registro por renglón del movimiento (CodigoMovimiento, IDArt, Entrada/Salida, CodDeposito, id_lote, etc.) | [tablas/stock.md](tablas/stock.md) |
| **stock_deposito** | Saldo por artículo y depósito. UPDATE Saldo o INSERT si no existe; bloquear con FOR UPDATE | [tablas/stock_deposito.md](tablas/stock_deposito.md) |
| **lote** / **lote_stock** | Lotes y saldo por lote/depósito cuando aplica | (consultar docs general/tablas si existen) |
| **ref_movstock** | Catálogo referencias (solo lectura en alta) | [tablas/ref_movstock.md](tablas/ref_movstock.md) |
| **movstock_pedi** | Relación movimiento ↔ pedido interno (comp_ped) | [tablas/movstock_pedi.md](tablas/movstock_pedi.md) |
| **serie_entrada_temp** / **serie_salida_temp** | Temporales de series por usuario (Mstock) | [tablas/serie_entrada_temp.md](tablas/serie_entrada_temp.md) |
| **lista_produccion_agrupada** / **lista_produccion_historico** | Motivos 10/11 (Pedido producción, Parte producción). En MPR el flujo OPP usa cantidad_pendiente_prod de lista_produccion_agrupada. | — |
| **stockp** | Cuerpo pedidos; motivo 11 en VB6 usaba cantidad_fab_pendiente_opt (*deprecado para MPR*). | [tablas/stockp.md](tablas/stockp.md) |

El esquema exacto de cada tabla (tipos, nulabilidad) se toma de la base MySQL o de los archivos en `docs/general/tablas/`. No se crean modelos Django para estas tablas; se usa el pool MySQL y servicios en Python.

## 2. Permisos Synap (key_permiso en permiso_sistema)

Se sincronizan con `sync_synap_permissions_to_adminet` / `asegurar_permisos_synap_si_procede`. Mapeo en backend a permisos de puesto AdministraNET:

| key_permiso | Nombre | Mapeo a permisos puesto |
|-------------|--------|--------------------------|
| **stock.ver** | Ver módulo Stock | Acceso al menú Stock |
| **stock.crear_movimiento** | Crear movimiento de stock | keyCompStock (Ingreso Mov. Stock); validar acceso_motivo_movstock, cambia_deposito, acceso_ref_movstock |
| **stock.consultas** | Consultas y anulaciones | keyConsultaStock, keyConsultaStockRap |
| **stock.ref_movstock** | ABM referencia movimiento | KeyABMref_movstock; validar acceso_ref_movstock / id_refmovstock |
| **stock.informes** | Informes de stock | keyInformesStock |
| **stock.*** | Acceso total Stock | Comodín para todos los anteriores |

Los puestos en AdministraNET siguen usando **permisos_sistema** (tabla ancha por IDPuesto: cambia_deposito, acceso_ref_movstock, acceso_motivo_movstock, deposito_usr, id_refmovstock, mov_stock_utiliza_cbarra). El backend revalida estos en cada alta/modificación.

### 2.1 Equivalencia menú VB6 (CargaMovStock) y acceso en Synap

El acceso a **"Ingreso Mov. Stock"** en Synap se considera equivalente a:

- **Menú y acceso al módulo:** tener `stock.crear_movimiento` en **permiso_sistema_puesto** **o** tener Clavemenu `keyCompStock` en la tabla **permisos** (mapeo automático en `get_permisos_totales_administranet`). Si el puesto tiene solo `keyCompStock` en permisos (asignado desde el formulario de roles en Synap o desde VB6), Synap otorga igualmente `stock.crear_movimiento` para menú y vistas.
- **Comportamiento dentro del formulario (depósitos, referencia, motivos):** mismos que CargaMovStock en VB6, gobernados por **permisos_sistema** (cambia_deposito, acceso_ref_movstock, acceso_motivo_movstock, id_refmovstock, id_deposito). Se editan en Synap en "Permisos del sistema" por puesto.

Al guardar permisos del menú para un puesto (`guardar_permisos_puesto`), si se asigna `keyCompStock` (y otras Clavemenu mapeadas en `MAPEO_MENU_A_PERMISO`), se sincroniza también **permiso_sistema_puesto** con el `key_permiso` correspondiente (`stock.crear_movimiento`, etc.) para mantener alineación. Ver [PERMISOS_STOCK_SYNAP_VS_VB6.md](PERMISOS_STOCK_SYNAP_VS_VB6.md).

## 3. Índices recomendados

Asegurar en la base de la empresa (o documentar para el DBA):

| Tabla | Índice | Propósito |
|-------|--------|-----------|
| **stock_deposito** | (id_articulo, id_deposito) o (IDArt, CodDeposito) según nombres reales | Búsqueda de saldo y bloqueo por fila en alta |
| **stock** | (CodigoMovimiento) | Consultas por movimiento y listados |
| **lote_stock** | (id_lote, id_deposito) | Saldo por lote/depósito y bloqueos |
| **cuerpostock_mstock** | (Codusuario, visualiza) | Limpieza de temporales y filtro por usuario |

Si alguna tabla usa nombres de columna distintos (ej. IDArt vs id_articulo), ajustar según el esquema real de la base.

## 4. Referencias

- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md): formularios, tablas, riesgos.
- [MOVIMIENTO_STOCK_CAMPOS_POR_MOTIVO.md](MOVIMIENTO_STOCK_CAMPOS_POR_MOTIVO.md): campos que dependen del motivo (cabecera y renglones), “movimiento en artículo” (TipoComp) y paridad VB6–Synap.
- Plan de migración: `.cursor/plans/migración_stock_inventario_synap_*.plan.md`.
