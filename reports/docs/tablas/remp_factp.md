# Tabla `remp_factp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_remp_factp | DOUBLE | No | ✓ |  |  |
| codigo_movimientof | DECIMAL | Sí |  |  |  |
| codigo_movimientor | DECIMAL | Sí |  |  |  |
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
| PNotaCred.frm | 2718 | SELECT | rs_consulta_remito.Open "SELECT * FROM remp_factp WHERE Anul… |
| PNotaCred.frm | 7594 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp " & _ |
| PNotaCred.frm | 7635 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp " & _ |
| OrdenPago.frm | 15309 | SELECT | '            rs_remp_factp.Open "SELECT * FROM remp_factp WH… |
| PRemito.frm | 4158 | SELECT | rs_rem_fact.Open "SELECT * FROM remp_factp WHERE id_remp_fac… |
| PFactura.frm | 5532 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp WHERE id_remp_f… |
| ConsultaComprobante.frm | 5196 | SELECT | rs_rem_fact.Open "SELECT * FROM remp_factp WHERE codigo_movi… |
| ConsultaComprobante.frm | 21628 | SELECT | '        rs_rem_fact.Open "SELECT * FROM remp_factp WHERE co… |
| ConsultaComprobante.frm | 21640 | SELECT | rs_rem_fact.Open "SELECT * FROM remp_factp WHERE codigo_movi… |
| ConsultaComprobante.frm | 22008 | SELECT | rs_rem_fact.Open "SELECT * FROM remp_factp WHERE codigo_movi… |
| ConsultaComprobante.frm | 29935 | SELECT | rs_consulta_remito.Open "SELECT * FROM remp_factp WHERE Anul… |
| ConsultaComprobante.frm | 30475 | SELECT | rs_rem_factp.Open "SELECT * FROM remp_factp WHERE codigo_mov… |
| Visualiza_PFactura_Copia.frm | 3613 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp WHERE id_remp_f… |
| trz_trazabilidadComp.frm | 1969 | JOIN | "LEFT OUTER JOIN remp_factp ON (remp_factp.codigo_movimiento… |
| trz_trazabilidadComp.frm | 1995 | JOIN | "LEFT OUTER JOIN remp_factp ON (remp_factp.codigo_movimiento… |
| trz_trazabilidadComp.frm | 2051 | JOIN | "LEFT OUTER JOIN remp_factp ON (remp_factp.codigo_movimiento… |
| trz_trazabilidadComp.frm | 2066 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2082 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2277 | JOIN | 'RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2296 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2317 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2334 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2524 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2546 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2564 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2596 | JOIN | '                                RIGHT OUTER JOIN remp_factp… |
| trz_trazabilidadComp.frm | 2703 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2721 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2740 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2760 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2780 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2836 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 2952 | JOIN | "RIGHT OUTER JOIN remp_factp ON (remp_factp.codigo_movimient… |
| trz_trazabilidadComp.frm | 3428 | SELECT | '            rs_remp_factp.Open "SELECT * FROM remp_factp WH… |
| Visualiza_OrdenPagoC.frm | 11133 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp WHERE codigo_mo… |
| PNotaCredCopia.frm | 2620 | SELECT | rs_consulta_remito.Open "SELECT * FROM remp_factp WHERE Anul… |
| PNotaCredCopia.frm | 7298 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp " & _ |
| PNotaCredCopia.frm | 7339 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp " & _ |
| Visualiza_PFacturaCopia2.frm | 3752 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp WHERE id_remp_f… |
| Visualiza_PFactura.frm | 3826 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp WHERE id_remp_f… |
| CuentaProveedor.frm | 2191 | SELECT | '            rs_remp_factp.Open "SELECT * FROM remp_factp WH… |
| Visualiza_OrdenPago.frm | 11535 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp WHERE codigo_mo… |
| ListaFacturasNC.frm | 1933 | SELECT | rs_remp_factp.Open "SELECT * FROM remp_factp WHERE codigo_mo… |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| management/commands/investigar_factura_stock.py | 137 | SELECT | FROM remp_factp rf |

[← Índice de tablas](../DB_INDICE_TABLAS.md)