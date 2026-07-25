# Tabla `ingreso_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ingreso | INT | No | ✓ |  |  |
| nombre_ingreso | VARCHAR | Sí |  |  |  |
| dato_adicional_ingreso | VARCHAR | Sí |  |  |  |
| detalle_ingreso | VARCHAR | Sí |  |  |  |
| id_caja_ingreso | INT | Sí |  |  |  |
| id_caja_acum | INT | Sí |  |  |  |
| id_pc | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc_gan | INT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7258 | SELECT | rs_caja_mc.Open "SELECT * FROM ingreso_abm WHERE id_ingreso … |
| Visualiza_ReciboCobro.frm | 7389 | SELECT | rs_caja_mc.Open "SELECT * FROM ingreso_abm WHERE id_ingreso … |
| Visualiza_ReciboCobro.frm | 9470 | SELECT | data_ingreso.RecordSource = "SELECT * FROM ingreso_abm WHERE… |
| Visualiza_ReciboCobro.frm | 14103 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| Visualiza_ReciboCobro.frm | 14261 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| Visualiza_ReciboCobro.frm | 15065 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| Liq_ABM_Viajante.frm | 835 | SELECT | data_viajantes_liq.RecordSource = "SELECT * FROM ingreso_abm… |
| OrdenPago.frm | 8153 | SELECT | rs_caja_consulta.Open "SELECT * FROM ingreso_abm WHERE id_in… |
| OrdenPago.frm | 14113 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| Visualiza_NotaDeb.frm | 2911 | SELECT | DataIngreso.RecordSource = "SELECT id_ingreso, nombre_ingres… |
| Lista_Ingresos.frm | 867 | SELECT | data_ingreso_combo.RecordSource = "SELECT * FROM ingreso_abm… |
| CargaIngreso.frm | 546 | SELECT | rs_ing.Open "SELECT * FROM ingreso_abm WHERE Nombre_ingreso … |
| CargaIngreso.frm | 562 | SELECT | rs_ing.Open "SELECT * FROM ingreso_abm WHERE  id_ingreso = 0… |
| CargaIngreso.frm | 583 | SELECT | ABM_ingreso.DataIng.RecordSource = "SELECT * from ingreso_ab… |
| CargaIngreso.frm | 595 | SELECT | rs_ing.Open "SELECT * FROM ingreso_abm WHERE id_ingreso = " … |
| NotaDeb.frm | 6027 | SELECT | DataIngreso.RecordSource = "SELECT id_ingreso, nombre_ingres… |
| Visualiza_OrdenPagoC.frm | 10060 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| NotaDebCopia.frm | 5863 | SELECT | DataIngreso.RecordSource = "SELECT id_ingreso, nombre_ingres… |
| ReciboCobro.frm | 7756 | SELECT | rs_caja_mc.Open "SELECT * FROM ingreso_abm WHERE id_ingreso … |
| ReciboCobro.frm | 7887 | SELECT | rs_caja_mc.Open "SELECT * FROM ingreso_abm WHERE id_ingreso … |
| ReciboCobro.frm | 10151 | SELECT | data_ingreso.RecordSource = "SELECT * FROM ingreso_abm WHERE… |
| ReciboCobro.frm | 15137 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| ReciboCobro.frm | 15295 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| ReciboCobro.frm | 16113 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| ABM_ingreso.frm | 467 | SELECT | DataIng.RecordSource = "SELECT * FROM ingreso_abm WHERE Nomb… |
| ABM_ingreso.frm | 546 | SELECT | DataIng.RecordSource = "select * from ingreso_abm order by N… |
| Visualiza_ReciboCobroC.frm | 7024 | SELECT | rs_caja_mc.Open "SELECT * FROM ingreso_abm WHERE id_ingreso … |
| Visualiza_ReciboCobroC.frm | 7155 | SELECT | rs_caja_mc.Open "SELECT * FROM ingreso_abm WHERE id_ingreso … |
| Visualiza_ReciboCobroC.frm | 9119 | SELECT | data_ingreso.RecordSource = "SELECT * FROM ingreso_abm WHERE… |
| Visualiza_ReciboCobroC.frm | 13720 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| Visualiza_ReciboCobroC.frm | 13878 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| Visualiza_ReciboCobroC.frm | 14682 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |
| Visualiza_OrdenPago.frm | 10462 | SELECT | rs_vect.Open "SELECT * from ingreso_abm where id_ingreso = "… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)