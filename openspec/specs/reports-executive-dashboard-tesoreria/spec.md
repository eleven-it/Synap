# Especificación — Dashboard gerencial: tesorería (caja)

**Capacidad:** `reports-executive-dashboard-tesoreria`  
**Origen archivado:** `adminnet-module-migration-command-center-finance` (14/07/2026)  
**Versión de contrato:** `executive-dashboard-v1` (hereda requisitos transversales de `reports-executive-dashboard`)

---

## Purpose

KPIs de **liquidez en caja** (`caja`, `caja_abm`) para el Command Center. No incluye libro banco (`librobanco`) en P0.

---

## Requirements

### REQ-ED-TES-01 — Ruta P0

- **`GET /api/reports/executive-dashboard/tesoreria/resumen/`** **MUST** existir y cumplir REQ-ED-SEC/FILT/META/ERR/TYPE del spec padre.

### REQ-ED-TES-02 — Alcance solo caja

- La respuesta **MUST** calcular saldos y flujos desde tabla **`caja`** (`anulado = 'No'`).
- La respuesta **MUST NOT** agregar montos de `librobanco` ni `cuenta_banco` en P0.
- **`banco_disponible`** **MUST** ser `false` en P0.

### REQ-ED-TES-03 — Saldos

| Campo | Definición |
|-------|------------|
| `saldo_inicial` | Suma del último `caja.Saldo` por `id_caja_abm_origen` con `fecha < fecha_inicio` (misma lógica que cash-flow waterfall) |
| `saldo_final` | Suma del último `caja.Saldo` por caja con `fecha <= fecha_fin` |

- Filtro `sucursal`: **MUST** restringir movimientos por `caja.cod_sucursal` cuando aplique.

### REQ-ED-TES-04 — Flujos operativos del período

| Campo | Definición |
|-------|------------|
| `ingresos_operativos` | SUM `ingreso` en período, excluyendo movimientos internos (REQ-ED-TES-05) |
| `egresos_operativos` | SUM `egreso` en período, misma exclusión |
| `variacion_neta` | `ingresos_operativos - egresos_operativos` |

### REQ-ED-TES-05 — Exclusión movimientos internos (vista consolidada)

- Del neto operativo **MUST** excluirse filas donde `caja.Tipo` contenga (case-insensitive) `Cierre de Caja` o `Transferencia de Fondos`.
- **`meta.notas_semanticas`** **MUST** indicar que transferencias y cierres no suman al neto consolidado.

### REQ-ED-TES-06 — Subcategorías

| Campo | Clasificación |
|-------|----------------|
| `ingresos_ventas` | Ingresos clasificados como ventas (FA/FB/FC/FE/FM según `_classify_movement`) |
| `ingresos_cobranzas` | Ingresos REC / cobranzas |
| `egresos_proveedores` | Egresos OP / compras proveedor |

### REQ-ED-TES-07 — Desglose por tipo de caja

- **`por_tipo_caja`** **MUST** ser arreglo con objetos `{ tipo_caja, ingresos, egresos, variacion }` agrupados por `caja_abm.tipo_caja` (JOIN origen).
- **SHOULD** limitar a tipos con movimiento en el período.

### REQ-ED-TES-08 — Disponibilidad

- **`disponible`**: `true` si la consulta finalizó; `false` + `error` en fallo transitorio (HTTP 503 en endpoint aislado).

### REQ-ED-TES-P1-01 — Banco (P1)

- **`GET .../tesoreria/banco/resumen/`** **MUST** implementarse sobre `librobanco` + `cuenta_banco`.
- La respuesta **MUST NOT** mezclarse con saldos de caja; el orquestador **MUST** anidar bajo `areas.tesoreria.banco`.

### REQ-ED-TES-P1-02 — Movimientos caja paginados

- **`GET .../tesoreria/movimientos-caja/`** **MUST** devolver `filas`, `total_registros`, `limit`, `offset`.
- **MUST** excluir cierres y transferencias internas del listado operativo.

---

## Escenarios

#### Scenario: Resumen caja con período válido

- GIVEN usuario con `ManagerialReportsPermission` y `base_empresa` válida
- WHEN `GET .../tesoreria/resumen/?fecha_inicio=2026-05-01&fecha_fin=2026-05-11`
- THEN respuesta 200 con `meta.definicion=executive-dashboard-v1`, `banco_disponible=false` y montos numéricos ≥ 0

#### Scenario: Período invertido

- GIVEN `fecha_inicio` posterior a `fecha_fin`
- WHEN `GET .../tesoreria/resumen/`
- THEN respuesta 400 con `error_type=invalid_data`

#### Scenario: Sin permiso

- GIVEN usuario sin permiso gerencial
- WHEN `GET .../tesoreria/resumen/`
- THEN respuesta 403

#### Scenario: MySQL no disponible

- GIVEN fallo de conexión legacy
- WHEN `GET .../tesoreria/resumen/`
- THEN respuesta 503 con `error_type=legacy_transient_failure`

#### Scenario: Nota semántica obligatoria

- GIVEN respuesta exitosa
- WHEN el cliente lee `meta.notas_semanticas`
- THEN incluye que no contempla libro banco en P0
