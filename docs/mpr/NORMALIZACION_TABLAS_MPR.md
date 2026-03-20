# Normalización de tablas DB (MPR / AdministraNET)

Documento de referencia de las tablas de base de datos usadas por el módulo MPR y sus relaciones, inferidas del código en `mpr/services.py`, `core` y la documentación de análisis MPR. Los nombres de tabla se resuelven en tiempo de ejecución con `_nombre_tabla()` (coincidencia case-insensitive con `SHOW TABLES`).

**Referencias:** [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md), [MANUAL_USUARIO_MPR.md](MANUAL_USUARIO_MPR.md), [TIPOS_DATOS_ADMINISTRANET.md](../general/TIPOS_DATOS_ADMINISTRANET.md).

---

## 1. Tablas y columnas (por uso en código)

### 1.1 Maestros

| Tabla | Columnas relevantes | Notas |
|-------|---------------------|--------|
| **articulo** | `IDArt` (PK), `CodigoArticulo`, `CodigoArticuloT`, `NombreArticulo`, `id_en_abm`, `ensamblado` ('Si'/'No'), `stock_reserva` (opc.), `stock_minimo` (opc.) | Artículo puede ser "armado" si `ensamblado='Si'` y `id_en_abm` no nulo. |
| **deposito** | `CodDeposito` (PK), `NombreDeposito`, `anulado` ('No'/'Si'), `suma_stock` ('Si'/'No', opc.) | Depósitos con `suma_stock='Si'` entran en stock terminado / Pedido producción trabajo (OPT). |
| **cliente** | `codigo` (PK), `nombre_cliente` | Usado en JOIN con `comp_ped` para listado de pedidos con estado de producción. |

### 1.2 Producción (órdenes y listas)

| Tabla | Columnas relevantes | Notas |
|-------|---------------------|--------|
| **lista_produccion_agrupada** | `id_lista_produccion` (PK, auto), `id_articulo`, `cantidad_pedida`, `cantidad_pendiente_prod`, `cantidad_fabricada_acumulada` (opc., acumulado OPA), `id_usuario`, `en_proceso_produccion` ('Si'/'No'), `id_deposito_produccion` (opc.), `prioridad` (opc.), `fecha_objetivo` (opc.) | Una fila por línea de OPT; varias filas pueden compartir el mismo `id_lista_produccion` (una OPT por lista). |
| **lista_produccion_detalle** | `id_lista_detalle` (PK, opc. tras ALTER), `id_lista_produccion` (FK a agrupada, opc.), `codigo_movimiento_pedido`, `id_articulo`, `cantidad_pedida`, `cantidad_pendiente_prod`, `en_proceso_produccion` | Detalle por pedido + artículo; origen demanda desde pedidos. **Trazabilidad:** `id_lista_produccion` → lista_produccion_agrupada.id_lista_produccion (script `sql/alter_lista_produccion_detalle_trazabilidad.sql`). |
| **lista_produccion_historico** | `id_articulo`, `id_articulo_formula`, `cantidad_pedida`, `cantidad_movimiento`, `cantidad_armada`, `id_deposito`, `codigo_movimiento_mstock`, `codigo_movimiento_opt` | Trazabilidad OPT/OPP: se escribe al liberar OPT y al registrar OPP; en OPP se persisten id_articulo (pack) y codigo_movimiento_opt (comprobante OPT). |

### 1.3 Lista de materiales (BOM / armado)

| Tabla | Columnas relevantes | Notas |
|-------|---------------------|--------|
| **en_abm** | `id_en_abm` (PK), `nombre_en_abm`, `detalle`, `anulado` ('No'/'Si'), `descuenta_en` (opc.) | Conjunto de armado (receta). |
| **en_abm_formula** | `id_en_abm_formula` (PK), `id_en_abm`, `id_articulo`, `cantidad_articulo`, `anulado`, `tipo_unidad` | Componentes del conjunto; una fila por (conjunto, artículo). |

### 1.4 Movimientos y stock

| Tabla | Columnas relevantes | Notas |
|-------|---------------------|--------|
| **movimiento_stock** | `codigo_movimiento` (PK), `nro_comprobante`, `motivo_movimiento`, `fecha`, `deposito_origen`, `deposito_destino`, `detalle`, `id_usuario`, `tipo_comprobante`, `anulado`, `id_ref_movstock`, `id_proyecto`, `id_cliente`, `id_vendedor`, `tipo_mov` (opc.), `id_pv` (opc.) | OPT, OPP y Armado usan `tipo_mov` / `motivo_movimiento` para distinguir. |
| **stock** | `CodigoMovimiento`, `IDArt`, `CodigoArticulo`, `Descripcion`, `Fecha`, `Entrada`, `Salida`, `saldo`, `CodDeposito`, `id_ref_movstock`, `Orden`, `IdUsuario`, `Tipo`, `TipoComp`, `Comprobante`, `NroComprobante`, `anulado`, `CodViajante` | Líneas de movimiento; saldo por línea. |
| **stock_deposito** | `id_stock_deposito` (PK), `id_articulo`, `id_deposito`, `saldo` | Saldo resumido por (artículo, depósito). |

### 1.5 Secuencias y pedidos

| Tabla | Columnas relevantes | Notas |
|-------|---------------------|--------|
| **codmov** | `codigo`, `CodigoMovimiento` | Secuencia de códigos de movimiento (p. ej. `codigo=1`). |
| **talonarios** | `Orden`, `Nro` | Numeración de comprobantes. |
| **comp_ped** | `CodigoMovimiento`, `NroComprobante`, `Fecha`, `Estado`, `TipoComprobante` ('PED'), **`estado_pedido_opt`** ('Pendiente' \| 'Produccion' \| 'Terminado'), `Anulado` | Pedidos de venta; estado_pedido_opt = estado de producción. Única fuente de demanda para fabricación cuando estado_pedido_opt='Pendiente'. |
| **deposito_reposicion** | `id_articulo`, `id_deposito`, `stock_minimo` (opc.) | Mínimos por artículo/depósito; usado en reporte "bajo mínimo". |

---

## 2. Relaciones (claves foráneas lógicas)

```
articulo
  ├── IDArt  ← lista_produccion_agrupada.id_articulo
  ├── IDArt  ← lista_produccion_detalle.id_articulo
  ├── IDArt  ← lista_produccion_historico.id_articulo
  ├── IDArt  ← en_abm_formula.id_articulo
  ├── IDArt  ← stock.IDArt
  ├── IDArt  ← stock_deposito.id_articulo
  ├── id_en_abm → en_abm.id_en_abm
  └── (deposito_reposicion.id_articulo, articulo.stock_minimo)

deposito
  ├── CodDeposito  ← stock_deposito.id_deposito
  ├── CodDeposito  ← movimiento_stock.deposito_origen / deposito_destino
  ├── CodDeposito  ← stock.CodDeposito
  ├── CodDeposito  ← lista_produccion_historico.id_deposito
  └── (lista_produccion_agrupada.id_deposito_produccion si existe)

en_abm
  ├── id_en_abm  ← en_abm_formula.id_en_abm
  └── id_en_abm  ← articulo.id_en_abm

movimiento_stock
  └── codigo_movimiento  ← stock (vía id_ref_movstock / CodigoMovimiento según uso)

lista_produccion_agrupada
  ├── id_lista_produccion  (PK; agrupa varias filas por OPT; mismo id = misma OPT)
  ├── id_lista_produccion  ← lista_produccion_detalle.id_lista_produccion (FK explícita tras ALTER de trazabilidad)
  └── id_lista_produccion  ← lista_produccion_historico.id_lista_produccion (FK lógico)

comp_ped
  └── codigo  → cliente.codigo (JOIN en listar_pedidos_fabrica)
```

---

## 3. Diagrama de relaciones (texto)

```
                    ┌─────────────┐
                    │  articulo   │
                    │ IDArt (PK)  │
                    │ id_en_abm   │──┐
                    │ ensamblado  │  │
                    └──────┬──────┘  │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
│ lista_produccion │ │ en_abm       │ │ en_abm_formula  │
│ _agrupada        │ │ id_en_abm(PK)│ │ id_en_abm ──────┤
│ id_articulo ─────┤ │ nombre_en_abm│ │ id_articulo ────┤
│ id_lista_prod(PK)│ └──────────────┘ │ cantidad_articulo│
│ cantidad_pedida  │                  └─────────────────┘
│ cantidad_pend_   │
│   iente_prod     │     ┌──────────────┐
│ en_proceso_prod  │     │  deposito     │
└────────┬─────────┘     │ CodDeposito  │
         │               │ suma_stock   │
         │               └──────┬──────┘
         │                      │
         │    ┌─────────────────┼─────────────────┐
         │    ▼                 ▼                  ▼
         │  stock_deposito   movimiento_stock   lista_prod_
         │  id_articulo      deposito_origen    historico
         │  id_deposito      deposito_destino   id_deposito
         │  saldo            codigo_movimiento
         │    │                    │
         └────┼────────────────────┼─────────────── stock
              │                    │               CodigoMov
              └────────────────────┴─────────────── codmov
                                                    CodigoMovimiento
```

---

## 4. Convenciones de tipos (AdministraNET)

Según reglas de proyecto y `core.utils.administranet_types`:

- **INT:** usar `to_int_or_none()`; no enviar strings numéricos sin convertir.
- **DATE:** usar `to_date_or_none()`; no enviar string vacío (usar `None`).
- **VARCHAR:** usar `str_or_default(valor, '-')` para opcionales vacíos.
- **DECIMAL:** usar `to_decimal_or_none()`.

Ver **docs/general/TIPOS_DATOS_ADMINISTRANET.md** si existe.

---

## 5. Flujo MPR y tablas afectadas

| Acción | Tablas leídas | Tablas escritas |
|--------|----------------|-----------------|
| Pedido producción trabajo (OPT) / demanda | lista_produccion_agrupada, articulo, stock_deposito, deposito | — |
| Crear OPT | lista_produccion_agrupada, articulo | lista_produccion_agrupada (INSERT) |
| Liberar OPT | lista_produccion_agrupada, articulo, codmov, talonarios, movimiento_stock, stock, stock_deposito | movimiento_stock, stock, stock_deposito, lista_produccion_agrupada (UPDATE), lista_produccion_historico (opc.) |
| Registrar OPP | lista_produccion_agrupada, codmov, talonarios, movimiento_stock, stock, stock_deposito | movimiento_stock, stock, stock_deposito, lista_produccion_agrupada (UPDATE cantidad_pendiente_prod) |
| Armado (OPA) | lista_produccion_agrupada (opc.), movimiento_stock, stock, stock_deposito, lista_produccion_historico | Incremento opcional `cantidad_fabricada_acumulada` si existe columna e `id_lista_produccion` |
| Armado | en_abm, en_abm_formula, articulo, stock_deposito, codmov, talonarios, movimiento_stock, stock | movimiento_stock, stock, stock_deposito |
| Cerrar OPT | lista_produccion_agrupada | lista_produccion_agrupada (UPDATE en_proceso_produccion='No') |
| Lista de materiales (BOM) | en_abm, en_abm_formula, articulo | en_abm, en_abm_formula, articulo (id_en_abm, ensamblado) |
