# Tabla `punto_venta_usr_info`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_punto_venta_usr_info | INT | No | ✓ |  |  |
| id_pv | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |

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
| Info_Impositivo.frm | 2351 | JOIN | "LEFT JOIN  punto_venta_usr_info ON (punto_venta_usr_info.id… |
| Info_Venta_respaldo_bruno.frm | 10055 | JOIN | "LEFT JOIN  punto_venta_usr_info ON (punto_venta_usr_info.id… |
| Info_Venta.frm | 10143 | JOIN | "LEFT JOIN  punto_venta_usr_info ON (punto_venta_usr_info.id… |
| AsigUsrPv_info.frm | 653 | SELECT | rs_exist.Open "SELECT * FROM punto_venta_usr_info WHERE id_p… |
| AsigUsrPv_info.frm | 712 | SELECT | conn.Execute "DELETE FROM punto_venta_usr_info WHERE id_punt… |
| AsigUsrPv_info.frm | 712 | DELETE | conn.Execute "DELETE FROM punto_venta_usr_info WHERE id_punt… |
| AsigUsrPv_info.frm | 759 | JOIN | "LEFT JOIN  punto_venta_usr_info ON (punto_venta_usr_info.id… |
| AsigUsrPv_info.frm | 887 | SELECT | conn.Execute "DELETE FROM punto_venta_usr_info WHERE id_usua… |
| AsigUsrPv_info.frm | 887 | DELETE | conn.Execute "DELETE FROM punto_venta_usr_info WHERE id_usua… |
| AsigUsrPv_info.frm | 898 | INSERT | conn.Execute "INSERT INTO punto_venta_usr_info (id_pv, id_us… |
| Info_RepRapidos.frm | 936 | JOIN | "LEFT JOIN  punto_venta_usr_info ON (punto_venta_usr_info.id… |
| Info_Cobranza.frm | 5672 | JOIN | "LEFT JOIN  punto_venta_usr_info ON (punto_venta_usr_info.id… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)