# Tabla `oc_presup`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_oc_presup | INT | No | ✓ |  |  |
| codigo_movimiento_oc | DECIMAL | Sí |  |  |  |
| codigo_movimiento_presup | DECIMAL | Sí |  |  |  |
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
| Visualiza_POrden_Compra.frm | 3712 | SELECT | rs_oc_presupuesto.Open "SELECT * FROM oc_presup WHERE id_oc_… |
| POrden_CompraCopia.frm | 3277 | SELECT | rs_oc_presupuesto.Open "SELECT * FROM oc_presup WHERE id_oc_… |
| ConsultaComprobante.frm | 18567 | SELECT | rs_oc_presup.Open "SELECT * FROM oc_presup WHERE Anulado = '… |
| ConsultaComprobante.frm | 18614 | SELECT | rs_oc_presup.Open "SELECT * FROM oc_presup WHERE Anulado = '… |
| ConsultaComprobante.frm | 18720 | SELECT | rs_oc_presup.Open "SELECT * FROM oc_presup WHERE Anulado = '… |
| Visualiza_POrden_CompraC.frm | 3178 | SELECT | rs_oc_presupuesto.Open "SELECT * FROM oc_presup WHERE id_oc_… |
| trz_trazabilidadComp.frm | 2028 | JOIN | "LEFT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_o… |
| trz_trazabilidadComp.frm | 2084 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2159 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2397 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2416 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2446 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2468 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2486 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2505 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2522 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2544 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2562 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2582 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2594 | JOIN | '                                RIGHT OUTER JOIN oc_presup … |
| trz_trazabilidadComp.frm | 2687 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2723 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2882 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| trz_trazabilidadComp.frm | 2999 | JOIN | "RIGHT OUTER JOIN oc_presup ON (oc_presup.codigo_movimiento_… |
| POrden_Compra.frm | 3943 | SELECT | rs_oc_presupuesto.Open "SELECT * FROM oc_presup WHERE id_oc_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)