# Tabla `departamento`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| IDDepartamento | INT | No | ✓ |  |  |
| NombreDepartamento | VARCHAR | Sí |  |  |  |
| CodProvincia | INT | No |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| cod_postal | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| configuracion | departamento | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 1581 | JOIN | var_left = var_left & " LEFT JOIN departamento ON (departame… |
| Cliente.frm | 2305 | SELECT | rs_domicilio.Open "select * from departamento where IDDepart… |
| Cliente.frm | 2996 | JOIN | "LEFT JOIN departamento ON (departamento.IDDepartamento = cl… |
| Cliente.frm | 3764 | SELECT | DataDepartamento2.RecordSource = "select * from departamento… |
| Info_Stock.frm | 11597 | SELECT | DataDepartamento.RecordSource = "SELECT * FROM Departamento … |
| Info_Stock.frm | 14178 | SELECT | DataDepartamento.RecordSource = "select * from departamento … |
| Visualiza_ReciboCobro.frm | 12322 | SELECT | rs_departamento.Open "SELECT * FROM departamento WHERE IDDep… |
| Visualiza_NotaCred.frm | 2488 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| Visualiza_NotaCred.frm | 2692 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| Visualiza_NotaCred.frm | 3009 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| CargaTransporte.frm | 922 | SELECT | DataDepartamento.RecordSource = "select * from Departamento … |
| CargaTransporte.frm | 1024 | SELECT | DataDepartamento.RecordSource = "select * from Departamento … |
| CargaTransporte.frm | 1031 | SELECT | DataDepartamento.RecordSource = "select * from Departamento … |
| Info_Estadistica.frm | 3495 | JOIN | '"From `configuracion`, ((((`cuentacliente` left join `clien… |
| Info_Estadistica.frm | 5950 | SELECT | DataDepartamento.RecordSource = "select * from Departamento … |
| Info_Estadistica.frm | 6138 | SELECT | DataDepartamento.RecordSource = "select * from departamento … |
| Info_Estadistica.frm | 6635 | SELECT | DataDepartamento.RecordSource = "select * from departamento … |
| Info_Estadistica.frm | 6927 | SELECT | DataDepartamento.RecordSource = "select * from departamento … |
| Info_Estadistica.frm | 6968 | SELECT | DataDepartamento.RecordSource = "select * from departamento … |
| NotaCredCon.frm | 3563 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 3885 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 4372 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 4635 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 4893 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 5138 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 5371 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 7796 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 9262 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 10432 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredCon.frm | 10983 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 5552 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 6061 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 6403 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 6694 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 12670 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 13489 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 14676 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| FacturaB_COPIA.frm | 18099 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 2928 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 3213 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 4835 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 5086 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 5339 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 5583 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 5830 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 6072 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 7589 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 8245 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCredDesc.frm | 8782 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 4486 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 5045 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 5297 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 5669 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 5905 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 9371 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 9983 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| NotaCred_COPIA.frm | 13102 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| Visualiza_TPV.frm | 7766 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| Visualiza_TPV.frm | 7956 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| Visualiza_TPV.frm | 8241 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| Visualiza_TPV.frm | 8401 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 17322 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 17576 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 17950 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 18192 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 21593 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 22484 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 23219 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 23834 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 26347 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 27508 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 28584 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 29735 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 30877 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 32437 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 32753 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 33088 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 36612 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| TPV.frm | 36935 | SELECT | rs_informe.Open "select * from departamento where idDepartam… |
| CuentaCliente.frm | 2753 | SELECT | rs_departamento.Open "SELECT * FROM departamento WHERE IDDep… |
| … | … | … | *(353 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)