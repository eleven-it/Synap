# Tabla `erp_pd_ped_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| id_erp_pd_ped_temp | INT | No | ✓ |  |  |

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
| Visualiza_Pedido.frm | 6567 | SELECT | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Visualiza_Pedido.frm | 6567 | DELETE | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Visualiza_Pedido.frm | 14606 | SELECT | '                rs_pd.Open "SELECT DISTINCT erp_pd_ped_temp… |
| Pedido.frm | 4663 | SELECT | rs_pd.Open "SELECT DISTINCT erp_pd_ped_temp.codigo_movimient… |
| Pedido.frm | 7856 | SELECT | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Pedido.frm | 7856 | DELETE | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Erp_Busqueda_PD.frm | 1595 | SELECT | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Erp_Busqueda_PD.frm | 1595 | DELETE | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Erp_Busqueda_PD.frm | 1670 | SELECT | rs_valid_ingreso_comp.Open "SELECT * FROM erp_pd_ped_temp WH… |
| Erp_Busqueda_PD.frm | 1679 | SELECT | rs_valid_ingreso_comp.Open "SELECT DISTINCT(id_proyecto) FRO… |
| Erp_Busqueda_PD.frm | 1814 | SELECT | rs_erp_pd_ped_temp.Open "SELECT * FROM erp_pd_ped_temp WHERE… |
| Principal.frm | 6083 | SELECT | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Principal.frm | 6083 | DELETE | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Principal.frm | 6149 | SELECT | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |
| Principal.frm | 6149 | DELETE | conn.Execute "delete from erp_pd_ped_temp where id_usuario =… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)