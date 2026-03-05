# Schema MPR – Base administranet (base_empresa)

Documento de referencia del esquema de base de datos usado por el módulo MPR en Synap. Base: **administranet** (por empresa, ej. administranet92). Actualizado según plan en [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md) y uso en `mpr/services.py`.

**Alcance:** MPR es un módulo **exclusivo de Synap**; la lógica de negocio de producción (OPT, OPP, lista_produccion_*, etc.) no existe en VB6/AdministraNET.

---

## 1. Resumen de tablas por rol

| Rol | Tablas |
|-----|--------|
| **Producción / OPT** | lista_produccion_agrupada, lista_produccion_detalle, lista_produccion_historico |
| **Movimientos de stock** | movimiento_stock (cabecera), stock (renglones), stock_deposito (saldos) |
| **Secuencia / comprobante** | codmov (CodigoMovimiento), talonarios (MSTOCK, Nro comprobante) |
| **Pedidos / demanda** | comp_ped (PED, tipo_pedido_opt: Pendiente \| Produccion \| Terminado), stockp (cantidad). *estado_pedido_opt y cantidad_fab_pendiente_opt deprecados para MPR; no usar "En proceso parcial/completo".* |
| **Lista de materiales / armado** | en_abm, en_abm_formula; articulo (ensamblado, id_en_abm) |
| **Catálogos** | articulo, deposito, deposito_reposicion, ref_movstock, unimed, presentacion_abm, viajantes |

---

## 2. Tablas con estructura y uso

### 2.1 movimiento_stock

**Documentación:** [tablas/movimiento_stock.md](tablas/movimiento_stock.md)

| Campo | Tipo | Uso MPR |
|-------|------|---------|
| ID_movimiento_stock | INT PK | — |
| codigo_movimiento | DECIMAL | Enlazado con codmov; Synap lo usa en alta OPT. |
| nro_comprobante | VARCHAR | Desde talonarios (MSTOCK). |
| motivo_movimiento | VARCHAR | 11 = Pedido producción (OPT). |
| fecha | DATE | Fecha del movimiento. |
| deposito_origen | INT | Origen (OPP: depósito de salida). |
| deposito_destino | INT | Destino (OPT: depósito de entrada producción). |
| tipo_mov | VARCHAR | 'OPT' = Pedido producción; 'OPP' = Parte producción. CargaMovStock.frm, Lista_Pedidos_OPT.frm; Synap escribe en alta. |
| id_ref_movstock | INT | Referencia movimiento (catálogo ref_movstock). |
| id_usuario, id_sucursal, id_pv | INT | Usuario y punto de venta. |
| detalle, anulado, estado, … | varios | Resto de campos estándar. |

---

### 2.2 stock

**Documentación:** [tablas/stock.md](tablas/stock.md)

| Campo | Tipo | Uso MPR |
|-------|------|---------|
| id_stock | BIGINT PK | — |
| CodigoMovimiento | DECIMAL | Mismo que movimiento_stock. |
| IDArt | INT | Artículo. |
| Entrada, Salida | DECIMAL | OPT: Entrada > 0, Salida 0. |
| saldo | DECIMAL | Saldo después del renglón. |
| CodDeposito | INT | Depósito (destino en OPT). |
| TipoComp | VARCHAR | Ej. 'MSTOCK'. |
| Comprobante, NroComprobante | VARCHAR | MSTOCK, nro desde talonarios. |
| Orden, IdUsuario, id_ref_movstock | INT | Renglón, usuario, referencia. |

---

### 2.3 stock_deposito

**Documentación:** [tablas/stock_deposito.md](tablas/stock_deposito.md)

| Campo | Tipo | Uso MPR |
|-------|------|---------|
| id_stock_deposito | DOUBLE PK | — |
| id_articulo | DECIMAL | Artículo. |
| id_deposito | INT | Depósito (CodDeposito en deposito). |
| saldo | DOUBLE | Saldo físico; MPR actualiza en OPT (INSERT o UPDATE). |
| saldo_pedido_cliente, saldo_pedido_proveedor | DOUBLE | Reservas. |

**Cálculo stock terminado (plan):** `SUM(stock_deposito.saldo)` por artículo donde `id_deposito` está en depósitos con `deposito.suma_stock = 'Si'`.

---

### 2.4 deposito

**Documentación:** [tablas/deposito.md](tablas/deposito.md)

| Campo | Tipo | Uso MPR |
|-------|------|---------|
| CodDeposito | INT PK | — |
| NombreDeposito | VARCHAR | Nombre mostrado. |
| Descripcion | TEXT | — |
| anulado | VARCHAR | Filtrar anulado = 'No'. |
| **suma_stock** | **VARCHAR(2)** | **Añadido por plan.** Default 'Si'. Si 'Si', el depósito suma al stock total para Pedido producción trabajo (OPT)/Unidades y reportes; si 'No' (tránsito, scrap, etc.) no suma. |

---

### 2.5 lista_produccion_agrupada

**Documentación:** No existe en tablas/; columnas inferidas de `mpr/services.py`. Estructura real leída de **administranet92**.

Agrupación por artículo de demanda de producción (órdenes de producción).

| Campo | Tipo | Uso |
|-------|------|-----|
| id_lista_produccion | BIGINT(20) PK, AUTO_INCREMENT | Identificador de OPT/agrupación. |
| id_articulo | BIGINT(20) | Artículo (FK lógico a articulo.IDArt). |
| cantidad_pedida | DOUBLE(15,2) DEFAULT 0 | Cantidad total pedida. |
| cantidad_pendiente_prod | DOUBLE(15,2) DEFAULT 0 | Pendiente de producir; MPR lo decrementa al liberar OPT. |
| id_usuario | INT(11) | Usuario. |
| en_proceso_produccion | VARCHAR(2) DEFAULT 'No' | Ej. 'Si'/'No'. |
| **fecha_objetivo** | **DATE NULL** | **Opcional.** Fecha objetivo de entrega; si la tabla no la tiene, MPR no muestra el campo en Nueva OPT. Añadir con script en `docs/general/sql/schema_mpr_administranet92.sql`. Usado para KPI "OPT atrasadas" (fecha_objetivo &lt; hoy y pendiente &gt; 0). |

**Uso en Synap:** Lectura en listado OP y detalle; UPDATE `cantidad_pendiente_prod = cantidad_pendiente_prod - &lt;qty&gt;` en `ejecutar_liberar_opt`. Si existe `fecha_objetivo`, se puede informar al crear la OPT (Nueva OPT) y mostrar en detalle.

**Nota:** En **administranet89** esta tabla no existía; en **administranet92** sí existe con la estructura anterior.

---

### 2.5.1 lista_produccion_agrupada_formula

**Documentación:** Estructura real leída de **administranet92**. No está referenciada en `mpr/services.py`.

Detalle por **artículo y componente de fórmula** (armado/unidad, pendientes, stock). No tiene columna `id_lista_produccion`; la relación con `lista_produccion_agrupada` es **lógica por id_articulo** (y opcionalmente id_articulo_formula).

| Campo | Tipo | Uso |
|-------|------|-----|
| id_lista_historico | BIGINT(20) PK, AUTO_INCREMENT | ID propio (no es FK a lista_produccion_agrupada). |
| id_articulo | BIGINT(20) | Artículo a fabricar (mismo concepto que en agrupada). |
| id_articulo_formula | BIGINT(20) | Componente de la fórmula/lista de materiales. |
| cantidad_pedida_armado | DOUBLE(15,2) | Cantidad pedida en armado. |
| cantidad_pendiente_prod_armado | DOUBLE(15,2) | Pendiente de producir (armado). |
| cantidad_pedida_unidad | DOUBLE(15,2) | Cantidad pedida en unidad. |
| cantidad_pendiente_prod_unidad | DOUBLE(15,2) | Pendiente en unidad. |
| cantidad_pedida_armado_stock | DOUBLE(15,2) | Armado desde stock. |
| cantidad_pendiente_prod_unidad_stock | DOUBLE(15,2) | Unidad desde stock. |
| tipo_art_fab | VARCHAR(20) | Tipo artículo fabricación. |
| id_usuario | INT(11) | Usuario. |
| en_proceso_produccion | VARCHAR(2) DEFAULT 'No' | Ej. 'Si'/'No'. |

**Relación con lista_produccion_agrupada:** No hay FK en `information_schema`. La relación es por **id_articulo** (y **id_articulo_formula**): las filas de `_formula` desglosan por componente (armado/unidad, pedido/pendiente/stock) la demanda del mismo artículo que aparece en `lista_produccion_agrupada`. Para vincular agrupada con fórmulas: JOIN por `id_articulo` (y opcionalmente filtrar por id_lista_produccion según criterio de agrupación en MPR).

**Alcance MPR:** La lógica de negocio de MPR (y de estas tablas lista_produccion_*) vive **solo en Synap**; no hay lógica equivalente en VB6/AdministraNET. **Nota:** Esta tabla no tiene ni requiere `fecha_objetivo`; la fecha objetivo es por OPT y va en `lista_produccion_agrupada`.

---

### 2.6 lista_produccion_detalle

**Documentación:** No existe en tablas/; columnas inferidas de `mpr/services.py`.

Detalle por pedido y artículo.

| Campo | Tipo | Uso |
|-------|------|-----|
| codigo_movimiento_pedido | INT | Pedido (comp_ped). |
| id_articulo | INT | Artículo. |
| cantidad_pedida | NUMERIC | Cantidad pedida. |
| cantidad_pendiente_prod | NUMERIC | Pendiente. |
| en_proceso_produccion | VARCHAR | Ej. 'Si'/'No'. |

---

### 2.7 lista_produccion_historico

**Documentación:** No existe en tablas/; columnas inferidas de `mpr/services.py`.

Trazabilidad de liberaciones OPT (insert opcional si la tabla existe).

| Campo | Tipo | Uso |
|-------|------|-----|
| id_articulo | INT | Artículo. |
| id_articulo_formula | INT/NULL | Componente fórmula si aplica. |
| cantidad_pedida | NUMERIC | Cantidad pedida en la línea. |
| cantidad_movimiento | NUMERIC | Cantidad liberada en este movimiento. |
| cantidad_armada | NUMERIC | 0 en OPT. |
| id_deposito | INT | Depósito destino. |
| codigo_movimiento_mstock | DECIMAL | CodigoMovimiento del movimiento. |
| codigo_movimiento_opt | DECIMAL | Mismo (OPT). |

---

### Relaciones entre lista_produccion_agrupada y lista_produccion_agrupada_formula

| Origen | Destino | Tipo de relación |
|--------|---------|-------------------|
| **lista_produccion_agrupada_formula** | **lista_produccion_agrupada** | **Sin FK declarada.** Enlace **lógico por `id_articulo`**: las filas de `_formula` desglosan por componente (`id_articulo_formula`) las cantidades (armado/unidad, pedido/pendiente/stock) del mismo artículo que en `lista_produccion_agrupada`. Una fila de agrupada (un id_articulo por id_lista_produccion) puede tener varias filas en _formula (una por componente). La tabla _formula tiene PK `id_lista_historico`, no `id_lista_produccion`. |
| lista_produccion_agrupada | articulo | FK lógico: `id_articulo` → articulo.IDArt (usado en JOIN en `mpr/services.py`). |

- En el **código Synap** no se usa `lista_produccion_agrupada_formula`; solo se lee/escribe `lista_produccion_agrupada`, `lista_produccion_detalle` y `lista_produccion_historico`.
- **administranet92:** ambas tablas existen; estructuras y relación anteriores tomadas de esa base. **administranet89:** no existían al inspeccionar.
- Para re-inspeccionar: `docker exec Synap_app python manage.py inspect_lista_produccion_tables <base_empresa>`.

---

### 2.8 codmov

**Documentación:** [tablas/codmov.md](tablas/codmov.md)

| Campo | Tipo | Uso MPR |
|-------|------|----------|
| codigo | INT PK | 1 para movimiento stock. |
| CodigoMovimiento | DOUBLE | Contador; SELECT FOR UPDATE, incrementar, UPDATE en la misma transacción que el alta. |

---

### 2.9 talonarios

**Documentación:** [tablas/talonarios.md](tablas/talonarios.md)

| Campo | Tipo | Uso MPR |
|-------|------|----------|
| TipoComprobante | VARCHAR | 'MSTOCK' para movimientos de stock. |
| id_punto_venta | INT | Punto de venta. |
| Nro | INT | Número de comprobante; SELECT FOR UPDATE, incrementar, UPDATE. |

---

### 2.10 comp_ped

**Documentación:** [tablas/comp_ped.md](tablas/comp_ped.md)

Cabecera de pedidos. Fuente de demanda MPR cuando tipo pedido a fábrica.

| Campo | Tipo | Uso MPR |
|-------|------|----------|
| CodigoMovimiento | DECIMAL | ID pedido. |
| TipoComprobante | VARCHAR | 'PED'. |
| tipo_pedido_opt | VARCHAR | Estado de producción del pedido: 'Pendiente', 'Produccion', 'Terminado'. Única fuente de demanda para fabricación cuando es 'Pendiente'. |
| estado_pedido_opt | VARCHAR | *(Deprecado para MPR.)* En VB6: Pendiente, En producción, En proceso parcial/completo, etc. MPR no usa este campo ni los estados "En proceso parcial/completo". |
| (resto) | varios | Fecha, cliente, estado, etc. |

---

### 2.11 stockp

**Documentación:** [tablas/stockp.md](tablas/stockp.md)

Renglones de pedidos (cuerpo). MPR no usa cantidad_fab_pendiente_opt; el pendiente de producción se gestiona en lista_produccion_agrupada.

| Campo | Tipo | Uso MPR |
|-------|------|----------|
| CodigoMovimiento | DECIMAL | Pedido (comp_ped). |
| IDArt | INT | Artículo. |
| Cantidad, cantidad_entregada | DECIMAL/DOUBLE | cantidad_pendiente_opt para reservado venta. *cantidad_fab_pendiente_opt deprecado para MPR.* |
| CodDeposito | INT | Depósito. |

---

### 2.12 en_abm, en_abm_formula

**Documentación:** [tablas/en_abm.md](tablas/en_abm.md), [tablas/en_abm_formula.md](tablas/en_abm_formula.md)

- **en_abm:** Conjuntos de armado (lista de materiales): id_en_abm, nombre_en_abm, anulado, detalle, descuenta_en.
- **en_abm_formula:** Componentes: id_en_abm, id_articulo, cantidad_articulo, anulado, tipo_unidad, cantidad_unidad_display, cantidad_dividir.

**articulo:** ensamblado='Si', id_en_abm para productos armados.

---

### 2.13 articulo

**Documentación:** [tablas/articulo.md](tablas/articulo.md)

| Campo | Tipo | Uso MPR |
|-------|------|----------|
| IDArt | INT PK | — |
| CodigoArticulo, CodigoArticuloT | INT/VARCHAR | Código mostrado. |
| NombreArticulo | VARCHAR | Descripción. |
| ensamblado | VARCHAR | 'Si' si es armado. |
| id_en_abm | DOUBLE | Conjunto de armado (en_abm). |
| multiplicador_vta | DECIMAL | Unidades por presentación (pack, docena). |
| **stock_reserva** | **DECIMAL(15,2)** | **Añadido por plan.** Stock de reserva por artículo; usado en Pedido producción trabajo (OPT)/Unidades: stock_reserva - stock_actual (depósitos con suma_stock='Si'). |

---

### 2.14 ref_movstock

**Documentación:** [tablas/ref_movstock.md](tablas/ref_movstock.md)

Catálogo de referencias de movimiento (id_ref_movstock, nombre_ref_movstock, anulado). MPR usa id_ref_movstock en alta de movimiento_stock y stock.

---

### 2.15 deposito_reposicion

Stock mínimo/máximo por artículo y depósito (stock_minimo, punto_pedido, etc.). Usado en alertas y en plan para evaluar contra el mismo “stock actual” (depósitos con suma_stock='Si').

---

### 2.16 unimed, presentacion_abm, viajantes

Catálogos para unidades de medida, presentaciones y viajantes; referenciados en el plan para etiquetado y ventanas MPR.

---

## 3. DDL para actualizar el schema (base_empresa)

Los siguientes cambios están definidos en el plan MPR; ejecutar en la base de la empresa (ej. administranet92) si las columnas no existen.

- **deposito:** agregar `suma_stock VARCHAR(2) DEFAULT 'Si'`.
- **articulo:** agregar `stock_reserva DECIMAL(15,2) DEFAULT NULL`.

**Formas de aplicarlo:**

1. **Comando Django (recomendado):** desde el contenedor, por cada base de empresa:
   ```bash
   docker exec Synap_app python manage.py apply_schema_mpr <base_empresa>
   ```
   Ejemplo: `apply_schema_mpr administranet89`. Opción `--dry-run` para solo mostrar los ALTER sin ejecutarlos. Si la columna ya existe, se omite.

2. **Script SQL:** [sql/schema_mpr_administranet92.sql](sql/schema_mpr_administranet92.sql) — ejecutar manualmente en MySQL contra la base correspondiente.

---

## 4. Referencias

- [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md) – Plan MPR (secciones 4.1, 4.2.1, 4.4).
- [ESQUEMA_TABLAS_STOCK_MIGRACION.md](ESQUEMA_TABLAS_STOCK_MIGRACION.md) – Stock y movimiento.
- `mpr/services.py` – Uso real de lista_produccion_*, movimiento_stock, stock, stock_deposito, codmov, talonarios.
- `docs/general/tablas/*.md` – Detalle de cada tabla documentada.
