# Tabla `oc_factp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_oc_factp | INT | No | ✓ |  |  |
| codigo_movimientof | DECIMAL | Sí |  |  |  |
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
| PFactura.frm | 5476 | SELECT | rs_pedido_factura.Open "SELECT * FROM oc_factp WHERE id_oc_f… |
| ConsultaComprobante.frm | 18666 | SELECT | rs_oc_factp.Open "SELECT * FROM oc_factp WHERE Anulado = 'No… |
| ConsultaComprobante.frm | 18736 | SELECT | rs_oc_factp.Open "SELECT * FROM oc_factp WHERE Anulado = 'No… |
| ConsultaComprobante.frm | 30314 | SELECT | rs_oc_factp.Open "SELECT * FROM oc_factp WHERE codigo_movimi… |
| ConsultaComprobante.frm | 30456 | SELECT | rs_oc_factp.Open "SELECT * FROM oc_factp WHERE codigo_movimi… |
| Visualiza_PFactura_Copia.frm | 3574 | SELECT | rs_oc_factp.Open "SELECT * FROM oc_factp WHERE id_oc_factp =… |
| trz_trazabilidadComp.frm | 2012 | JOIN | "LEFT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof = … |
| trz_trazabilidadComp.frm | 2027 | JOIN | "LEFT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof = … |
| trz_trazabilidadComp.frm | 2177 | SELECT | "From oc_factp " & _ |
| trz_trazabilidadComp.frm | 2211 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimiento_oc… |
| trz_trazabilidadComp.frm | 2231 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimiento_oc… |
| trz_trazabilidadComp.frm | 2247 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimiento_oc… |
| trz_trazabilidadComp.frm | 2276 | JOIN | 'RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimiento_oc… |
| trz_trazabilidadComp.frm | 2415 | SELECT | "From oc_factp " & _ |
| trz_trazabilidadComp.frm | 2447 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimiento_oc… |
| trz_trazabilidadComp.frm | 2469 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimiento_oc… |
| trz_trazabilidadComp.frm | 2487 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimiento_oc… |
| trz_trazabilidadComp.frm | 2595 | JOIN | '                                RIGHT OUTER JOIN oc_factp O… |
| trz_trazabilidadComp.frm | 2704 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof =… |
| trz_trazabilidadComp.frm | 2722 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof =… |
| trz_trazabilidadComp.frm | 2852 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof =… |
| trz_trazabilidadComp.frm | 2881 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof =… |
| trz_trazabilidadComp.frm | 2969 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof =… |
| trz_trazabilidadComp.frm | 2998 | JOIN | "RIGHT OUTER JOIN oc_factp ON (oc_factp.codigo_movimientof =… |
| Visualiza_PFacturaCopia2.frm | 3713 | SELECT | rs_oc_factp.Open "SELECT * FROM oc_factp WHERE id_oc_factp =… |
| Visualiza_PFactura.frm | 3787 | SELECT | rs_oc_factp.Open "SELECT * FROM oc_factp WHERE id_oc_factp =… |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| management/commands/investigar_factura_stock.py | 114 | SELECT | FROM oc_factp ocf |
| services/reconciliation_saldo_pedido_proveedor.py | 211 | JOIN | INNER JOIN oc_factp ocf ON ocf.codigo_movimientof = s.Codigo… |
| services/reconciliation_saldo_pedido_proveedor.py | 461 | JOIN | INNER JOIN oc_factp ocf ON ocf.codigo_movimientof = s.Codigo… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)