# Tabla `en_orden`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_orden | DOUBLE | No | ✓ |  |  |
| nro_comp | VARCHAR | Sí |  |  |  |
| nro_comp_busq | INT | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| estado_en_orden | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_deposito_entrada | DOUBLE | Sí |  |  |  |
| id_deposito_salida | DOUBLE | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_proyecto | DOUBLE | Sí |  |  |  |
| detalle_en_orden | MEDIUMTEXT | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| fecha_entrega | DATE | Sí |  |  |  |
| fecha_control | TIMESTAMP | Sí |  |  |  |
| id_sucursal | BIGINT | Sí |  |  |  |

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
| En_GeneraOE.frm | 3235 | SELECT | rs_EnO.Open "SELECT * FROM en_orden WHERE id_en_orden = 0", … |
| En_GeneraOE.frm | 4852 | SELECT | "From en_orden " & _ |
| En_GestionOE.frm | 790 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento =  en_ord… |
| En_GestionOE.frm | 816 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento =  en_ord… |
| En_GestionOE.frm | 851 | JOIN | '                            "LEFT JOIN en_orden ON (en_orde… |
| En_GestionOE.frm | 1507 | SELECT | rs_enOrden.Open "SELECT En_orden.*,cliente.nombre_Cliente FR… |
| ConsultaComprobante.frm | 3214 | SELECT | DataConsulta.RecordSource = "select en_orden.*, cliente.Nomb… |
| ConsultaComprobante.frm | 3222 | SELECT | DataConsulta.RecordSource = "select en_orden.*, cliente.Nomb… |
| ConsultaComprobante.frm | 3308 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento = en_poe.… |
| ConsultaComprobante.frm | 3326 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento = en_poe.… |
| ConsultaComprobante.frm | 25677 | SELECT | rs_OE.Open "SELECT * FROM en_orden WHERE Codigo_Movimiento =… |
| ConsultaComprobante.frm | 25963 | SELECT | rs_OE.Open "SELECT * FROM en_orden WHERE Codigo_Movimiento =… |
| ConsultaComprobante.frm | 26062 | SELECT | rs_orden.Open "SELECT en_orden.*, cliente.nombre_cliente, de… |
| Visualiza_En_GeneraOE.frm | 4337 | SELECT | rs_EnO.Open "SELECT * FROM en_orden WHERE Codigo_movimiento … |
| Visualiza_En_GeneraOE.frm | 4725 | SELECT | '        rs_est.Open "SELECT estado_en_orden FROM en_orden W… |
| Visualiza_En_GeneraOE.frm | 5185 | SELECT | rs_EnO.Open "SELECT * FROM en_orden WHERE Codigo_movimiento … |
| Visualiza_En_GeneraOE.frm | 5687 | JOIN | "RIGHT JOIN en_orden ON (en_orden.codigo_movimiento = en_ord… |
| Visualiza_En_GeneraOE.frm | 5693 | JOIN | "RIGHT JOIN en_orden ON (en_orden.codigo_movimiento = en_ord… |
| Visualiza_En_GeneraOE.frm | 5726 | JOIN | "RIGHT JOIN en_orden ON (en_orden.codigo_movimiento = en_ord… |
| Visualiza_En_GeneraOE.frm | 5989 | SELECT | rs_orden.Open "SELECT en_orden.*, cliente.nombre_cliente, de… |
| VisualizarFichaArt.frm | 2884 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento = en_orde… |
| VisualizarFichaArt.frm | 3321 | SELECT | '        "From en_orden " & _ |
| En_GeneraPOE.frm | 2460 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento =  en_ord… |
| En_GeneraPOE.frm | 2482 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento =  en_ord… |
| En_GeneraPOE.frm | 2678 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento = en_poe.… |
| Principal.frm | 11981 | JOIN | "LEFT JOIN en_orden ON (en_orden.codigo_movimiento = en_poe.… |
| Visualiza.bas | 8030 | SELECT | DataConsulta.Open "select en_orden.*, cliente.Nombre_cliente… |
| Visualiza.bas | 8079 | SELECT | rs_enOrden.Open "SELECT En_orden.*,cliente.nombre_Cliente FR… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)