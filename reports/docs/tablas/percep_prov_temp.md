# Tabla `percep_prov_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percep_prov_temp | BIGINT | No | ✓ |  |  |
| id_jurisdiccion | BIGINT | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| importe_percep | DOUBLE | Sí |  |  |  |
| id_proveedor | BIGINT | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |

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
| PNotaCred.frm | 2981 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PNotaCred.frm | 5785 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaCred.frm | 5785 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaCred.frm | 6555 | SELECT | "FROM percep_prov_temp " & _ |
| POrden_CompraCopia.frm | 3013 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| POrden_CompraCopia.frm | 5514 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| POrden_CompraCopia.frm | 5514 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaDebCopia.frm | 1910 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PNotaDebCopia.frm | 4034 | SELECT | "FROM percep_prov_temp " & _ |
| PNotaDebCopia.frm | 4740 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaDebCopia.frm | 4740 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PFactura.frm | 4213 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PFactura.frm | 8173 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PFactura.frm | 8173 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PFactura.frm | 9261 | SELECT | "FROM percep_prov_temp " & _ |
| PPresupuesto.frm | 3343 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PPresupuesto.frm | 5718 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PPresupuesto.frm | 5718 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaCred_Importe.frm | 2120 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PNotaCred_Importe.frm | 3812 | SELECT | "FROM percep_prov_temp " & _ |
| PNotaCred_Importe.frm | 4613 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaCred_Importe.frm | 4613 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| percep_ib_compras.frm | 485 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| percep_ib_compras.frm | 518 | SELECT | data_grid_percepcion.RecordSource = "SELECT percep_prov_temp… |
| percep_ib_compras.frm | 530 | SELECT | data_grid_percepcion.RecordSource = "SELECT percep_prov_temp… |
| percep_ib_compras.frm | 546 | SELECT | rs_total_percep.Open "SELECT SUM(percep_prov_temp.importe_pe… |
| percep_ib_compras.frm | 551 | SELECT | rs_total_percep.Open "SELECT SUM(percep_prov_temp.importe_pe… |
| percep_ib_compras.frm | 598 | SELECT | conn.Execute "DELETE FROM percep_prov_temp WHERE id_percep_p… |
| percep_ib_compras.frm | 598 | DELETE | conn.Execute "DELETE FROM percep_prov_temp WHERE id_percep_p… |
| percep_ib_compras.frm | 705 | SELECT | conn.Execute "DELETE from percep_prov_temp WHERE id_usuario … |
| percep_ib_compras.frm | 705 | DELETE | conn.Execute "DELETE from percep_prov_temp WHERE id_usuario … |
| percep_ib_compras.frm | 714 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| percep_ib_compras.frm | 856 | SELECT | conn.Execute "DELETE from percep_prov_temp WHERE id_usuario … |
| percep_ib_compras.frm | 856 | DELETE | conn.Execute "DELETE from percep_prov_temp WHERE id_usuario … |
| percep_ib_compras.frm | 865 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PNotaDeb.frm | 2004 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PNotaDeb.frm | 4260 | SELECT | "FROM percep_prov_temp " & _ |
| PNotaDeb.frm | 4966 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaDeb.frm | 4966 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaCredCopia.frm | 2883 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| PNotaCredCopia.frm | 5510 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaCredCopia.frm | 5510 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |
| PNotaCredCopia.frm | 6259 | SELECT | "FROM percep_prov_temp " & _ |
| POrden_Compra.frm | 3621 | SELECT | rs_percep_prov_temp.Open "SELECT * FROM percep_prov_temp WHE… |
| POrden_Compra.frm | 6405 | SELECT | conn.Execute "delete from percep_prov_temp where id_usuario … |
| POrden_Compra.frm | 6405 | DELETE | conn.Execute "delete from percep_prov_temp where id_usuario … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)