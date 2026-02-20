# Tabla `ped_presup`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ped_presup | DOUBLE | No | ✓ |  |  |
| codigo_movimiento_ped | DECIMAL | Sí |  |  |  |
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
| Visualiza_Pedido.frm | 14558 | SELECT | '                    rs_pedido_presupuesto.Open "SELECT * FR… |
| Visualiza_Pedido.frm | 14660 | SELECT | '                    rs_pedido_presupuesto.Open "SELECT * FR… |
| trz_trazabilidad.frm | 2407 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2463 | JOIN | "LEFT OUTER JOIN ped_presup ON (ped_presup.codigo_movimiento… |
| trz_trazabilidad.frm | 2555 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2574 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2605 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2626 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2644 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2663 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2681 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2703 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2721 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2741 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2799 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 2808 | JOIN | sql_rc = sql_rc & "INNER JOIN ped_presup as pp ON (cp.Codigo… |
| trz_trazabilidad.frm | 3128 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 3164 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 3242 | JOIN | sql_rc = sql_rc & "INNER JOIN ped_presup as pp ON (cp.Codigo… |
| trz_trazabilidad.frm | 3343 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 3465 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| trz_trazabilidad.frm | 3588 | JOIN | "RIGHT OUTER JOIN ped_presup ON (ped_presup.codigo_movimient… |
| NotaCredCopia.frm | 15528 | SELECT | rs_ped_presup.Open "SELECT * FROM ped_presup WHERE codigo_mo… |
| Pedido.frm | 4615 | SELECT | rs_pedido_presupuesto.Open "SELECT * FROM ped_presup WHERE i… |
| Pedido.frm | 4717 | SELECT | rs_pedido_presupuesto.Open "SELECT * FROM ped_presup WHERE i… |
| ConsultaComprobante.frm | 10101 | SELECT | rs_ped_presup.Open "SELECT * FROM ped_presup WHERE codigo_mo… |
| ConsultaComprobante.frm | 10268 | SELECT | rs_ped_presup.Open "SELECT * FROM ped_presup WHERE codigo_mo… |
| ConsultaComprobante.frm | 31281 | SELECT | rs_ped_presup.Open "SELECT * FROM ped_presup WHERE codigo_mo… |
| NotaCred.frm | 16211 | SELECT | rs_ped_presup.Open "SELECT * FROM ped_presup WHERE codigo_mo… |
| Anulaciones.bas | 79 | SELECT | '            rs_ped_presup.Open "SELECT * FROM ped_presup WH… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)