# Inventario de esquema cont_* — auditoría contable

**Change:** `contabilidad-auditoria-recalculo` (Fase 0)  
**Base piloto verificada:** `administranet89` (18/07/2026)  
**Comando:** `docker exec Synap_app python manage.py verificar_esquema_cont --base-empresa=administranet89`

## Resumen

Se verificó el esquema real vía `information_schema` en la base piloto. Los nombres de columnas de periodo usan sufijo `_periodo` (`fecdesde_periodo`, `fechasta_periodo`), no `fecdesde`/`fechasta` genéricos del borrador inicial.

## Tablas y columnas clave

### cont_asiento (21 columnas)

| Columna | Tipo | Nullable | Uso en checks |
|---------|------|----------|---------------|
| debe_asiento | decimal | YES | Saldo teórico, balance |
| haber_asiento | decimal | YES | Saldo teórico, balance |
| anulado | varchar | YES | Filtro política anulados |
| id_concepto_asiento | double | YES | Conceptos, compras/pagos |
| saldo_asiento | decimal | YES | Check compra/pago NULL |
| codigo_movimiento | decimal | YES | Enlace comprobantes |
| codigo_movimiento_anul | decimal | YES | Anulaciones |
| id_ejercicio | double | YES | Filtro corrida |
| id_periodo | double | YES | Saldo periodo |
| fecha_asiento | date | YES | Fecha vs periodo |
| nro_asiento | double | YES | Duplicados |

### cont_pc (24 columnas)

| Columna | Tipo | Notas |
|---------|------|-------|
| saldo_pc | varchar | Valores: `Deudor`, `Acreedor`, NULL, `''` |
| imp_cont_pc | varchar | `Imputable` vs contenedora |
| cod_pc | varchar | Prefijos política |
| ajuste_infla_pc | varchar | Check REI |

### cont_concepto_asiento

| Columna | Tipo | Notas |
|---------|------|-------|
| id_concepto_anul | int | Emparejamiento anulación (no +1) |
| tipo_concepto_asiento | varchar | Debe ser `Normal` |
| tipo_concepto | varchar | Consistencia H37 |

### cont_periodo

| Columna | Tipo | Notas |
|---------|------|-------|
| fecdesde_periodo | date | Intervalo periodo |
| fechasta_periodo | date | Intervalo periodo |
| cerrado | varchar | `Si`/`No` |

**Hallazgo empírico:** en `administranet89` la tabla puede estar **vacía**; los checks de periodo deben tolerar ausencia de filas sin abortar.

### cont_ejercicio

| Columna | Tipo |
|---------|------|
| nro_asiento_ejercicio | double NOT NULL |
| fecdesde_ejercicio / fechasta_ejercicio | date |
| activo_ejercicio / cerrado | varchar |

### Saldos derivados

- `cont_ejercicio_saldo_cta(id_pc, id_ejercicio, saldo_ejercicio_cta)`
- `cont_periodo_saldo_cta(id_pc, id_ejercicio, id_periodo, saldo_periodo_cta)`

### Compras / pagos

- `cuentaproveedor.CodigoMovimiento` ↔ `cont_asiento.codigo_movimiento`
- Tipos: FA/FC (concepto 3), OP (concepto 7)
- `CodigoMovimiento=0`: marcador anulación (excluir de “sin asiento”)
- `punto_venta.cont='Si'`: PV contable (gating REC-18 compras/pagos y REC-20 ventas/cobranzas)
- `sucursales.cont='Si'`: sucursal contable (flag VB6 `Principal.conta_suc`; no sustituye gating por PV en Synap)

## Desviaciones respecto al design inicial

1. Periodos: columnas `fecdesde_periodo` / `fechasta_periodo` (no `fecdesde`/`fechasta`).
2. `cont_periodo` puede no tener filas en empresas piloto.
3. `saldo_pc` admite NULL y string vacío además de Deudor/Acreedor.

## Verificación automatizada

El comando `verificar_esquema_cont` valida existencia de tablas/columnas listadas arriba sin emitir DML.
