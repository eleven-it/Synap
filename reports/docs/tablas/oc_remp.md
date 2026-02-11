# Tabla `oc_remp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_oc_remp | INT | No | ✓ |  |  |
| codigo_movimiento_remp | DECIMAL | Sí |  |  |  |
| codigo_movimiento_oc | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

*No se encontraron JOINs que involucren esta tabla en el código escaneado.*

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| PRemito.frm | 4049 | SELECT | '                rs_oc_remp.Open "SELECT * FROM oc_remp WHER… |
| PRemito.frm | 4098 | SELECT | rs_rem_ped.Open "SELECT * FROM oc_remp WHERE id_oc_remp = 0"… |
| ConsultaComprobante.frm | 5347 | SELECT | rs_rem_ped.Open "SELECT * FROM oc_remp WHERE codigo_movimien… |
| ConsultaComprobante.frm | 18656 | SELECT | rs_oc_remp.Open "SELECT * FROM oc_remp WHERE Anulado = 'No' … |
| ConsultaComprobante.frm | 18728 | SELECT | rs_oc_remp.Open "SELECT * FROM oc_remp WHERE Anulado = 'No' … |
| ConsultaComprobante.frm | 21928 | SELECT | rs_rem_oc.Open "SELECT * FROM oc_remp WHERE codigo_movimient… |
| ConsultaComprobante.frm | 21984 | SELECT | rs_rem_ped.Open "SELECT * FROM oc_remp WHERE codigo_movimien… |
| trz_trazabilidadComp.frm | 2067 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_remp… |
| trz_trazabilidadComp.frm | 2083 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_remp… |
| trz_trazabilidadComp.frm | 2265 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2295 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2316 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2333 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2356 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2506 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2523 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2545 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2563 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2583 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_oc =… |
| trz_trazabilidadComp.frm | 2644 | SELECT | rs_RemPed.Open "select * From oc_remp " & _ |
| trz_trazabilidadComp.frm | 2671 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_remp… |
| trz_trazabilidadComp.frm | 2686 | JOIN | "RIGHT OUTER JOIN oc_remp ON (oc_remp.codigo_movimiento_remp… |
| Visualiza_PRemito.frm | 3327 | SELECT | rs_oc_remp.Open "SELECT * FROM oc_remp WHERE id_oc_remp = 1"… |
| Visualiza_PRemitoC.frm | 3155 | SELECT | rs_oc_remp.Open "SELECT * FROM oc_remp WHERE id_oc_remp = 1"… |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/reconciliation_saldo_pedido_proveedor.py | 192 | JOIN | INNER JOIN oc_remp ocrem ON ocrem.codigo_movimiento_remp = s… |
| services/reconciliation_saldo_pedido_proveedor.py | 440 | JOIN | INNER JOIN oc_remp ocrem ON ocrem.codigo_movimiento_remp = s… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)