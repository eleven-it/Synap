# Exploración: tesorería en AdministraNET

**Cambio:** `adminnet-module-migration-command-center-finance`  
**Fecha:** 19/05/2026  
**Alcance:** flujo legacy de caja y bancos para Command Center (sin migrar pantallas).

---

## 1. Dos subsistemas de tesorería (no mezclar)

AdministraNET maneja la liquidez en **dos capas paralelas** que se vinculan por `codigo_movimiento` pero **no comparten el mismo saldo**:

| Subsistema | Tablas maestras | Libro de movimientos | Uso operativo |
|------------|-----------------|----------------------|---------------|
| **Caja** | `caja_abm`, `caja_saldo` | `caja` | Efectivo PV, cobranzas en mostrador, pagos efectivo, cheques en cartera, tarjetas en caja dedicada, cierres |
| **Banco** | `cuenta_banco`, `banco` | `librobanco` | Cuentas corrientes, transferencias, boletas de depósito, OP bancarias, conciliación |

**Regla para KPIs:** el Command Center gerencial debe mostrar **caja** y **banco** como bloques distintos. Sumar `caja` + `librobanco` en un único “saldo total” **duplica o distorsiona** (un cobro puede generar movimiento en caja y luego depósito en banco).

---

## 2. Capa Caja — modelo de datos

### 2.1 `caja_abm` (maestro)

Cada **caja lógica** (no confundir con `caja.id_caja` = PK del movimiento).

| Campo | Rol |
|-------|-----|
| `id_caja` | PK caja |
| `nombre_caja`, `tipo_caja` | Etiqueta y rol funcional |
| `id_sucursal` | Sucursal |
| `anulado`, `limite_efectivo` | Estado y controles |

**Tipos funcionales** (filtros VB6): Acumulativa, Punto de Venta, Fondo Fijo, Cheque, Acumulativa Cheque, Tarjeta, Acumulativa Tarjeta, Otro Medio de Cobro, etc.

**Usuarios** (`usuarios`): cada operador tiene cajas asignadas — `id_caja`, `id_caja_deposito`, `id_caja_tarjeta`, `id_caja_cheque`, … Cargadas en `Principal` al login.

### 2.2 `caja_saldo` (saldo contable por caja y moneda)

- Un registro por (`id_caja`, `Moneda`) con `Saldo` actual.
- **Alta de caja:** se crean filas Pesos (y Dólar si Acumulativa/Punto de Venta).
- **Cada movimiento VB6:** tras INSERT en `caja`, se hace **UPDATE `caja_saldo.Saldo`** (+ ingreso / − egreso).

**Brecha Synap:** `write_caja_ingreso` (MercadoPago / TPV) hoy inserta en `caja` pero **no actualiza `caja_saldo`** (`docs/self_checkout/CAJA_AUTOSERVICIO_ANALISIS_Y_GAPS.md`). El saldo “oficial” en VB6 vive en `caja_saldo`; el informe cash-flow de Synap usa el campo **`caja.Saldo`** del último movimiento por caja.

### 2.3 `caja` (diario de movimientos)

Cada fila = un hecho de tesorería en una caja origen (y opcionalmente destino).

| Campo | Rol |
|-------|-----|
| `id_caja` | PK movimiento |
| `codigo_movimiento` | Contador compartido con factura, REC, OP, MCAJ |
| `Fecha` / `fecha_control` | Fecha operación |
| `ingreso`, `egreso` | Siempre ≥ 0; uno en cero |
| `Saldo` | Saldo **después** del movimiento en esa caja (origen) |
| `id_caja_abm_origen`, `id_caja_abm_destino` | Cajas afectadas |
| `tipo_comprobante` | FA, FB, REC, OP, MCAJ, CHEQ, TARJ, … |
| `Tipo` | Texto negocio: `Factura Contado TPV`, `Cobranza Efectivo`, `Pago Efectivo`, `Cierre de Caja - Usuario de PV`, `Transferencia de Fondos`, … |
| `tipo_cp` | Cliente / Proveedor / Mov Caja |
| `cod_sucursal`, `cod_vendedor` | Filtros gerenciales |
| `id_cierre_caja` | Agrupa movimientos de un cierre PV |
| `anulado` | Si → reversa en `caja_saldo` en VB6 |
| `importe_fisico`, `importe_diferencia`, `arqueo_cerrado` | Post-arqueo |

**Convención:** ingreso puro = `ingreso > 0`, `egreso = 0`; egreso puro al revés.

---

## 3. Procesos que escriben en `caja` (mapa completo)

### 3.1 Ventas y cobranzas (ya cubiertos en exploration-cobros)

| Origen VB6 | Caja | Tipo típico |
|------------|------|-------------|
| TPV / Factura contado | `id_caja_abm_origen` = caja usuario / tarjeta / cheque | `Factura Contado TPV`, `Tarjeta` |
| ReciboCobro | Caja elegida / tarjeta / cheque | `Cobranza Efectivo`, etc. |
| MercadoPago (Synap) | `id_caja_abm` config MP | `Tarjeta` |

### 3.2 Pagos a proveedores

| Origen | Efecto |
|--------|--------|
| `OrdenPago.frm` | **Egreso** en caja (efectivo o cheque); puede generar fila en `librobanco` si pago bancario |

### 3.3 Movimientos manuales — `CargaMovCaja.frm`

| Operación | Origen | Destino | Efecto en saldo |
|-----------|--------|---------|-----------------|
| Ingreso manual | — | caja | + ingreso |
| Egreso / retiro | caja | — | − egreso |
| **Transferencia entre cajas** | caja A | caja B | egreso en A + ingreso en B (mismo `codigo_movimiento`) |
| Cierre a supervisor | caja PV | caja acumulativa/supervisor | egreso PV + ingreso destino |
| Cobro cheque en efectivo | caja cheque | caja efectivo | según tipo |

`nro_comprobante` tipo **MCAJ** + contador.

### 3.4 Cierre de caja PV y arqueo

**Cierre Usuario PV** (`CargaMovCaja`):

1. INSERT `caja` egreso en caja PV (`Tipo` = `Cierre de Caja - Usuario de PV`).
2. UPDATE `caja_saldo` PV.
3. Asignar `id_cierre_caja` a movimientos del PV sin cerrar.
4. INSERT ingreso en caja destino (depósito / acumulativa).
5. Contador en `caja_cierre`.

**Arqueo** (`Caja_Arqueo.frm`):

- Lista cierres con `arqueo_cerrado = 'No'`.
- Conteo por denominación → `caja_arqueo`.
- UPDATE `caja` con `importe_fisico`, `importe_diferencia`, `arqueo_cerrado = 'Si'`.

Tablas: `caja_cierre`, `caja_arqueo`, `viajantes`.

### 3.5 Otros

- `CargaDNF_Caja`, `CargaExtraccion` — egresos varios.
- Anulaciones — `caja.anulado = 'Si'` + reverso saldo.

### 3.6 Movimientos internos (doble partida)

Cuando se ven **todas las cajas** agregadas:

- **Transferencia de Fondos** y **Cierre de Caja** generan ingreso y egreso que se **cancelan** a nivel empresa.
- `query_runner._run_cash_flow_waterfall` **excluye** explícitamente esos `Tipo` del `operating_flow` consolidado (líneas 959–964).

Cuando se filtra **una caja**, el movimiento cuenta (solo se ve el lado origen o destino de esa caja).

---

## 4. Capa Banco — modelo de datos

### 4.1 Maestros

- **`banco`** — entidad bancaria.
- **`cuenta_banco`** — cuenta (`CodCuenta`, `CodBanco`, `NroCuenta`, `saldo`, `moneda`).

### 4.2 `librobanco` (movimientos)

| Campo | Rol |
|-------|-----|
| `CodMov` | PK |
| `CodCuenta`, `CodBanco` | Cuenta |
| `CodigoMovimiento` | Enlace a OP, REC, transferencia, boleta, etc. |
| `Debito`, `Credito`, `Saldo` | Importes y saldo corrido |
| `Fecha`, `CodSucursal` | Filtros |
| `id_transf`, `id_boletadeposito`, `id_gastobancario`, `id_tc_liquidacion`, `id_clearing` | Origen del movimiento |
| `conciliado`, `fecha_conciliado` | Conciliación bancaria |
| `Anulado` | Baja lógica |

### 4.3 Procesos que escriben en `librobanco`

| Formulario / proceso | Rol |
|----------------------|-----|
| `CargaTransBancaria.frm` | Transferencias bancarias |
| `CargaBDeposito.frm` | Boleta de depósito |
| `OrdenPago.frm` | Pagos desde cuenta bancaria |
| `ReciboCobro.frm` | Cobros con transferencia (fecha en libro) |
| `CargaGastoBancario.frm` | Gastos bancarios |
| `CargaLiquidacionTC.frm` | Liquidación tarjetas |
| `CargaClearing.frm`, `CargaDeudaBancaria.frm`, `CargaAjusteLB.frm` | Ajustes |
| `LibroBanco.frm` | Consulta |

**Synap:** sin lectura en `reports/` hoy — **gap P1**.

### 4.4 `transferencia` y `boletadeposito`

- **`transferencia`:** cabecera transferencia (`id_cuentabancaria`, `importe_transf`, `codigo_movimiento`) → alimenta `librobanco`.
- **`boletadeposito`:** depósito físico en banco (`CargaBDeposito`) → `librobanco` con `id_boletadeposito`.

Puente típico: efectivo en **caja** → cierre / boleta → **librobanco**.

---

## 5. Clasificación en informes Synap (reutilizable)

`reports/services/query_runner.py`:

### 5.1 `_classify_movement(tipo_comprobante, tipo, …)`

Clasifica cada fila de **`caja`** en:

- **Flujo:** operativo / inversión / financiamiento (casi todo operativo).
- **Subcategoría ingresos:** `ingresos_ventas` (FA/FB/FC…), `ingresos_cobranzas` (REC, CHEQ cliente), `ingresos_intereses`, `ingresos_otros`.
- **Subcategoría egresos:** `egresos_proveedores` (OP, FA proveedor), `egresos_impuestos` (gastos grupo/nombre impuesto), `egresos_sueldos`, `egresos_servicios`, `egresos_gastos`, `egresos_otros`.

### 5.2 `_get_payment_method(tipo_comprobante, tipo)`

Heurística sobre **`caja`** (no `medio_cobpag`): Efectivo, Cheque, Tarjeta, Transferencia, Recibo, etc.

### 5.3 Informes existentes (POST `/api/reports/query/`)

| Slug | Qué calcula |
|------|------------|
| `cash_flow_waterfall` | Saldo inicial (último `caja.Saldo` antes del período), flujo mensual operativo/inversión/financiamiento, ingresos/egresos operativos |
| `cash_flow_by_account` | Por cada `caja_abm`: saldo ini/fin, flujos |
| `cash_flow_detailed_movements` | Detalle fila a fila con `medio_pago`, subcategoría, join `gastos` |

**Filtros:** `fecha_inicio`, `fecha_fin`, `id_caja` (una o varias), `cod_sucursal` vía movimiento.

---

## 6. Qué debe mostrar el Command Center — área `tesoreria`

### P0 — Caja (obligatorio)

Basado en agregación `caja` (misma semántica que cash-flow), **sin** detalle masivo:

| KPI | Definición |
|-----|------------|
| `saldo_caja_inicial` / `saldo_caja_final` | Último `caja.Saldo` por caja agregado (o por sucursal si filtro) |
| `ingresos_operativos`, `egresos_operativos`, `variacion_neta` | SUM ingreso/egreso período; excluir transferencias/cierres en vista consolidada |
| `ingresos_ventas` | Subconjunto clasificado FA/FB… |
| `ingresos_cobranzas` | Subconjunto REC / cobranzas |
| `egresos_proveedores` | Subconjunto OP / compras |
| `por_tipo_caja[]` | Opcional: Acumulativa vs PV vs Tarjeta (top 3–4 tipos) |
| `cajas_con_movimiento` | COUNT DISTINCT `id_caja_abm_origen` |

**Notas meta obligatorias:**

- Transferencias internas excluidas del neto consolidado.
- Diferencia posible entre `caja.Saldo` corrido y `caja_saldo` si hay movimientos solo desde Synap sin update de saldo maestro.
- No incluye saldos bancarios.

### P1 — Banco (librobanco)

| KPI | Definición |
|-----|------------|
| `saldo_banco_inicial` / `final` | Último `librobanco.Saldo` por `CodCuenta` antes/después período |
| `creditos_periodo`, `debitos_periodo` | SUM en rango |
| `por_cuenta_banco[]` | Desglose por `cuenta_banco` + nombre banco |
| `pendiente_conciliar` | COUNT donde `conciliado` ≠ 'Si' (si columna poblada) |

Requiere **SQL nuevo** (no existe en Python reports).

### P2 — Control operativo (fuera P0 gerencial)

- Cierres pendientes de arqueo (`arqueo_cerrado = 'No'`).
- Límites de efectivo por caja (`caja_abm.limite_efectivo`).

---

## 7. Relación caja ↔ banco (para documentación UI)

```text
[Cliente paga efectivo en PV]
        → caja (ingreso, caja PV)
        → (cierre PV) → caja acumulativa
        → (boleta depósito) → librobanco (crédito en cuenta)

[Cliente paga transferencia]
        → librobanco (crédito) + puede haber registro en caja según configuración REC

[OP proveedor banco]
        → librobanco (débito)
        → puede haber egreso espejo en caja si pago desde caja efectivo
```

---

## 8. Riesgos y validaciones UAT

| Riesgo | Mitigación |
|--------|------------|
| Doble conteo caja+banco en un KPI | Etiquetas separadas; no sumar |
| Transferencias inflan ingresos/egresos | Excluir `Transferencia de Fondos` y `Cierre de Caja` en neto global |
| `caja_saldo` desactualizado vs `caja.Saldo` | Documentar; P2 alinear Synap write con VB6 |
| `librobanco` sin código | P1 con spike SQL en empresa piloto |
| Cheques en cartera vs efectivo | Clasificación por `tipo_caja` Cheque y `tipo_comprobante` CHEQ |

---

## 9. Referencias Synap

| Recurso | Ruta |
|---------|------|
| Procesos caja | `docs/self_checkout/CAJA_ADMINISTRANET_PROCESOS.md` |
| Cierre y arqueo | `docs/self_checkout/TPV_CAJA_AUTENTICACION_Y_OPERACIONES.md` |
| Gaps autoservicio caja | `docs/self_checkout/CAJA_AUTOSERVICIO_ANALISIS_Y_GAPS.md` |
| Cash flow SQL | `reports/services/query_runner.py` (`_run_cash_flow_*`, `_classify_movement`) |
| Tablas | `docs/general/tablas/caja.md`, `caja_abm.md`, `caja_saldo.md`, `librobanco.md`, `cuenta_banco.md`, `transferencia.md` |
