# Tabla `reporte_comp_vtas_gast_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_reporte_cvg | INT | No | ✓ |  |  |
| id_usuario | INT | Sí |  |  |  |
| yearp | INT | Sí |  |  |  |
| mesp | INT | Sí |  |  |  |
| compras | DECIMAL | Sí |  |  |  |
| ventas | DECIMAL | Sí |  |  |  |
| gastos | DECIMAL | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| tipocomprobante | VARCHAR | Sí |  |  |  |
| total | DECIMAL | Sí |  |  |  |
| tiporesumen | VARCHAR | Sí |  |  |  |

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
| Info_Estadistica.frm | 2698 | SELECT | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Info_Estadistica.frm | 2698 | DELETE | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Info_Estadistica.frm | 2711 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Info_Estadistica.frm | 2717 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Info_Estadistica.frm | 2723 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Info_Estadistica.frm | 2734 | INSERT | '    insertar = " INSERT INTO reporte_comp_vtas_gast_temp (`… |
| Info_Estadistica.frm | 2739 | INSERT | insertar = "INSERT INTO reporte_comp_vtas_gast_temp (`id_usu… |
| Info_Estadistica.frm | 2772 | INSERT | InsertarCompras = " INSERT INTO reporte_comp_vtas_gast_temp … |
| Info_Estadistica.frm | 2789 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Info_Estadistica.frm | 2927 | SELECT | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Info_Estadistica.frm | 2927 | DELETE | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Info_Estadistica.frm | 2941 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Info_Estadistica.frm | 2947 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Info_Estadistica.frm | 2957 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Info_Estadistica.frm | 2963 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2837 | SELECT | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Erp_Info.frm | 2837 | DELETE | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Erp_Info.frm | 2843 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2849 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2855 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2864 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2870 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2876 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2962 | SELECT | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Erp_Info.frm | 2962 | DELETE | conn.Execute "DELETE FROM reporte_comp_vtas_gast_temp WHERE … |
| Erp_Info.frm | 2967 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2973 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2984 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Erp_Info.frm | 2990 | INSERT | conn.Execute " INSERT INTO reporte_comp_vtas_gast_temp (`id_… |
| Principal.frm | 6122 | SELECT | conn.Execute "delete from reporte_comp_vtas_gast_temp where … |
| Principal.frm | 6122 | DELETE | conn.Execute "delete from reporte_comp_vtas_gast_temp where … |
| Principal.frm | 6188 | SELECT | conn.Execute "delete from reporte_comp_vtas_gast_temp where … |
| Principal.frm | 6188 | DELETE | conn.Execute "delete from reporte_comp_vtas_gast_temp where … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)