# Tabla `ped_fact`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ped_fact | DOUBLE | No | ✓ |  |  |
| CodigoMovimientoP | DECIMAL | Sí |  |  |  |
| CodigoMovimientoF | DECIMAL | No |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |

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
| FacturaB_COPIA.frm | 5077 | SELECT | rs_pedido_factura.Open "SELECT * FROM ped_fact WHERE id_ped_… |
| NotaCred_COPIA.frm | 4047 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| TPV.frm | 10169 | SELECT | rs_pedido_factura.Open "SELECT * FROM ped_fact WHERE id_ped_… |
| trz_trazabilidad.frm | 2391 | JOIN | "LEFT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = c… |
| trz_trazabilidad.frm | 2406 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 2575 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2606 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2627 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2645 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2664 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2853 | SELECT | "From ped_fact " & _ |
| trz_trazabilidad.frm | 2883 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2903 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2919 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 2937 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoP = … |
| trz_trazabilidad.frm | 3145 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3163 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3306 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3342 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3428 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3464 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3552 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3587 | JOIN | "RIGHT OUTER JOIN ped_fact ON (ped_fact.CodigoMovimientoF = … |
| FacturaB.frm | 6220 | SELECT | rs_pedido_factura.Open "SELECT * FROM ped_fact WHERE id_ped_… |
| FacturaB.frm | 9051 | SELECT | rs_pedido_factura.Open "SELECT * FROM ped_fact WHERE id_ped_… |
| NotaCred_SinCompO.frm | 5019 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| FacturaA.frm | 5941 | SELECT | rs_pedido_factura.Open "SELECT * FROM ped_fact WHERE id_ped_… |
| NotaCredCopia.frm | 4619 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| NotaCredCopia.frm | 15476 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 6203 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 6346 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 7764 | SELECT | '                    rs_ped_fact.Open "SELECT * FROM ped_fac… |
| ConsultaComprobante.frm | 7907 | SELECT | '        rs_ped_fact.Open "SELECT * FROM ped_fact WHERE Codi… |
| ConsultaComprobante.frm | 10225 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 31229 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| NotaCred.frm | 4763 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| NotaCred.frm | 16159 | SELECT | rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMovimie… |
| TPV_2.frm | 9900 | SELECT | rs_pedido_factura.Open "SELECT * FROM ped_fact WHERE id_ped_… |
| Anulaciones.bas | 25 | SELECT | '    rs_ped_fact.Open "SELECT * FROM ped_fact WHERE CodigoMo… |
| Funciones.bas | 14604 | SELECT | " FROM ped_fact " & _ |
| Funciones.bas | 15029 | SELECT | " FROM ped_fact " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)