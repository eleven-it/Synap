# Tabla `rem_ped`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_rem_ped | DOUBLE | No | ✓ |  |  |
| NroRemito | VARCHAR | Sí |  |  |  |
| NroPedido | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| codmov_remito | DECIMAL | Sí |  |  |  |
| codmov_pedido | DECIMAL | Sí |  |  |  |

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
| trz_trazabilidad.frm | 2446 | JOIN | "LEFT OUTER JOIN rem_ped ON (rem_ped.codmov_remito = rem_fac… |
| trz_trazabilidad.frm | 2462 | JOIN | "LEFT OUTER JOIN rem_ped ON (rem_ped.codmov_remito = rem_fac… |
| trz_trazabilidad.frm | 2682 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido = ped_pr… |
| trz_trazabilidad.frm | 2704 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido = ped_pr… |
| trz_trazabilidad.frm | 2722 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido = ped_pr… |
| trz_trazabilidad.frm | 2742 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido= ped_pre… |
| trz_trazabilidad.frm | 2955 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido = comp_p… |
| trz_trazabilidad.frm | 2976 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido = comp_p… |
| trz_trazabilidad.frm | 2993 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido = comp_p… |
| trz_trazabilidad.frm | 3014 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_pedido = comp_p… |
| trz_trazabilidad.frm | 3024 | JOIN | '                                 "LEFT OUTER JOIN rem_ped O… |
| trz_trazabilidad.frm | 3085 | SELECT | rs_RemPed.Open "select * From rem_ped " & _ |
| trz_trazabilidad.frm | 3112 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_remito = comp_p… |
| trz_trazabilidad.frm | 3127 | JOIN | "RIGHT OUTER JOIN rem_ped ON (rem_ped.codmov_remito = comp_p… |
| trz_trazabilidad.frm | 3324 | JOIN | "LEFT OUTER JOIN rem_ped  ON (rem_ped.codmov_remito = rem_fa… |
| trz_trazabilidad.frm | 3446 | JOIN | "LEFT OUTER JOIN rem_ped  ON (rem_ped.codmov_remito = rem_fa… |
| trz_trazabilidad.frm | 3569 | JOIN | "LEFT OUTER JOIN rem_ped  ON (rem_ped.codmov_remito = rem_fa… |
| Remito.frm | 5084 | SELECT | rs_rem_ped.Open "SELECT * FROM rem_ped WHERE id_rem_ped = 0"… |
| Visualiza_RemitoCopia.frm | 3325 | SELECT | rs_rem_ped.Open "SELECT * FROM rem_ped WHERE id_rem_ped = 0"… |
| ConsultaComprobante.frm | 10236 | SELECT | rs_rem_ped.Open "SELECT * FROM rem_ped WHERE codmov_pedido =… |
| ConsultaComprobante.frm | 21007 | SELECT | rs_rem_ped.Open "SELECT * FROM rem_ped WHERE codmov_remito =… |
| ConsultaComprobante.frm | 21064 | SELECT | rs_rem_ped.Open "SELECT * FROM rem_ped WHERE codmov_remito =… |
| trz_trazabilidadComp.frm | 2866 | JOIN | '#LEFT OUTER JOIN rem_ped  ON (rem_ped.codmov_remito = rem_f… |
| trz_trazabilidadComp.frm | 2983 | JOIN | '    #LEFT OUTER JOIN rem_ped  ON (rem_ped.codmov_remito = r… |
| Visualiza_Remito.frm | 3362 | SELECT | rs_rem_ped.Open "SELECT * FROM rem_ped WHERE id_rem_ped = 0"… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)