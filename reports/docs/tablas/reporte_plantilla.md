# Tabla `reporte_plantilla`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_plantilla | DOUBLE | No | ✓ |  |  |
| nombre_plantilla | VARCHAR | Sí |  |  |  |
| path_reporte | VARCHAR | Sí |  |  |  |
| texto_plantilla | MEDIUMTEXT | Sí |  |  |  |
| tipo_plantilla | VARCHAR | Sí |  |  |  |
| id_articulo | BIGINT | Sí |  |  |  |

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
| Configuracion2.frm | 4987 | SELECT | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion2.frm | 4987 | DELETE | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion2.frm | 5413 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Presupuesto'… |
| Configuracion2.frm | 5999 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Presupuesto'… |
| Configuracion2.frm | 6011 | SELECT | "FROM reporte_plantilla " & _ |
| Configuracion2.frm | 6025 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Orden de com… |
| Configuracion.frm | 5084 | SELECT | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion.frm | 5084 | DELETE | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion.frm | 5512 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Presupuesto'… |
| Configuracion.frm | 6100 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Presupuesto'… |
| Configuracion.frm | 6112 | SELECT | "FROM reporte_plantilla " & _ |
| Configuracion.frm | 6126 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Orden de com… |
| POrden_CompraCopia.frm | 3418 | SELECT | "FROM reporte_plantilla " & _ |
| POrden_CompraCopia.frm | 4930 | SELECT | rs_existP.Open "SELECT * FROM reporte_plantilla ", conn, adO… |
| POrden_CompraCopia.frm | 4939 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Orden de com… |
| Presupuesto.frm | 4383 | SELECT | "FROM reporte_plantilla " & _ |
| Presupuesto.frm | 6511 | SELECT | rs_existP.Open "SELECT * FROM reporte_plantilla ", conn, adO… |
| Presupuesto.frm | 6520 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Presupuesto'… |
| ConsultaComprobante.frm | 14742 | SELECT | "FROM reporte_plantilla " & _ |
| ConsultaComprobante.frm | 15916 | SELECT | "FROM reporte_plantilla " & _ |
| Carga_plantilla.frm | 528 | INSERT | conn.Execute "INSERT INTO reporte_plantilla(nombre_plantilla… |
| Carga_plantilla.frm | 542 | UPDATE | conn.Execute "UPDATE reporte_plantilla SET " & _ |
| POrden_Compra.frm | 4087 | SELECT | "FROM reporte_plantilla " & _ |
| POrden_Compra.frm | 5770 | SELECT | rs_existP.Open "SELECT * FROM reporte_plantilla ", conn, adO… |
| POrden_Compra.frm | 5779 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Orden de com… |
| Configuracion_COPIA.frm | 4586 | SELECT | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion_COPIA.frm | 4586 | DELETE | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion_COPIA.frm | 4875 | SELECT | "FROM reporte_plantilla " |
| Configuracion.frm | 5434 | SELECT | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion.frm | 5434 | DELETE | conn.Execute "DELETE FROM reporte_plantilla WHERE id_plantil… |
| Configuracion.frm | 5832 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Presupuesto'… |
| Configuracion.frm | 6369 | SELECT | "FROM reporte_plantilla WHERE tipo_plantilla = 'Presupuesto'… |
| Configuracion.frm | 6381 | SELECT | "FROM reporte_plantilla " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)