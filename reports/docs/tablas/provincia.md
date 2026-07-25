# Tabla `provincia`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodProvincia | INT | No | ✓ |  |  |
| Provincia | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |
| cod_afip | INT | Sí |  |  |  |
| id_juridic_convenio | INT | Sí |  |  |  |
| id_pc | INT | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| configuracion | provincia | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 1580 | JOIN | var_left = var_left & " LEFT JOIN provincia ON (provincia.Co… |
| Cliente.frm | 2301 | SELECT | rs_domicilio.Open "select * from provincia where CodProvinci… |
| Cliente.frm | 2995 | JOIN | "LEFT JOIN provincia ON (provincia.CodProvincia = cliente_do… |
| Cliente.frm | 3185 | SELECT | DataProvincia2.RecordSource = "select * from provincia WHERE… |
| Info_Stock.frm | 11603 | SELECT | DataProvincia.RecordSource = "SELECT * FROM provincia WHERE … |
| PNotaCred.frm | 4509 | SELECT | DataProvincia.RecordSource = "select * from Provincia" |
| PNotaCred.frm | 6556 | JOIN | "INNER JOIN provincia ON (codProvincia = id_jurisdiccion) " … |
| Visualiza_ReciboCobro.frm | 12321 | SELECT | rs_provincia.Open "SELECT * FROM provincia WHERE CodProvinci… |
| Visualiza_NotaCred.frm | 2493 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| Visualiza_NotaCred.frm | 2697 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| Visualiza_NotaCred.frm | 3014 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| CargaTransporte.frm | 927 | SELECT | DataProvincia.RecordSource = "select * from Provincia order … |
| Info_Estadistica.frm | 3495 | JOIN | '"From `configuracion`, ((((`cuentacliente` left join `clien… |
| Info_Estadistica.frm | 5944 | SELECT | DataProvincia.RecordSource = "select * from provincia order … |
| Info_Estadistica.frm | 8756 | JOIN | " LEFT JOIN `provincia` ON (`provincia`.`CodProvincia` = `cl… |
| Info_Estadistica.frm | 8775 | JOIN | " LEFT JOIN `provincia` ON (`provincia`.`CodProvincia` = `cl… |
| Info_Estadistica.frm | 8792 | JOIN | " LEFT JOIN `provincia` ON (`provincia`.`CodProvincia` = `cl… |
| Info_Estadistica.frm | 8811 | JOIN | " LEFT JOIN `provincia` ON((`provincia`.`CodProvincia` = `cl… |
| Info_Estadistica.frm | 8936 | JOIN | " LEFT JOIN `provincia` ON (`provincia`.`CodProvincia` = `cl… |
| Info_Estadistica.frm | 8957 | JOIN | " LEFT JOIN `provincia` ON (`provincia`.`CodProvincia` = `cl… |
| Info_Estadistica.frm | 8976 | JOIN | " LEFT JOIN `provincia` ON (`provincia`.`CodProvincia` = `cl… |
| Info_Estadistica.frm | 8997 | JOIN | " LEFT JOIN `provincia` ON((`provincia`.`CodProvincia` = `cl… |
| NotaCredCon.frm | 3568 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 3890 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 4377 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 4640 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 4898 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 5143 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 5376 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 7801 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 9267 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 10437 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredCon.frm | 10988 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| Visualiza_PNotaDeb.frm | 2141 | SELECT | DataProvincia.RecordSource = "select * from provincia" |
| FacturaB_COPIA.frm | 5557 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| FacturaB_COPIA.frm | 6066 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| FacturaB_COPIA.frm | 6408 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| FacturaB_COPIA.frm | 6699 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| FacturaB_COPIA.frm | 12675 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| FacturaB_COPIA.frm | 13494 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| FacturaB_COPIA.frm | 14681 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| FacturaB_COPIA.frm | 18104 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 2933 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 3218 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 4840 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 5091 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 5344 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 5588 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 5835 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 6077 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 7594 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 8250 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCredDesc.frm | 8787 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 4491 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 5050 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 5302 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 5674 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 5910 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 9376 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 9988 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| NotaCred_COPIA.frm | 13107 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| CargaSucursal.frm | 1410 | SELECT | DataProvincia.RecordSource = "select * from Provincia where … |
| CargaSucursal.frm | 1414 | SELECT | DataProvincia.RecordSource = "select * from Provincia order … |
| CargaSucursal.frm | 1849 | SELECT | DataProvincia.RecordSource = "select * from provincia where … |
| CargaSucursal.frm | 1857 | SELECT | DataProvincia.RecordSource = "select * from provincia where … |
| Visualiza_TPV.frm | 7771 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| Visualiza_TPV.frm | 7961 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| Visualiza_TPV.frm | 8246 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| Visualiza_TPV.frm | 8406 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 17327 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 17581 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 17955 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 18197 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 21598 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 22489 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 23224 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 23839 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 26352 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 27513 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| TPV.frm | 28589 | SELECT | rs_informe.Open "select * from provincia where CodProvincia … |
| … | … | … | *(403 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)