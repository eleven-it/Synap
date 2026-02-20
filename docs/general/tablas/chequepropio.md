# Tabla `chequepropio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| NroCheque | DECIMAL | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| NroChequera | VARCHAR | Sí |  |  |  |
| CodCuenta | INT | Sí |  |  |  |
| CodProveedor | INT | Sí |  |  |  |
| CodChequera | INT | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| FechaEmision | DATE | Sí |  |  |  |
| FechaCobro | DATE | Sí |  |  |  |
| FechaVto | DATE | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| NroOP | VARCHAR | Sí |  |  |  |
| ID | DOUBLE | No | ✓ |  |  |
| CodigoMovimientoOP | DECIMAL | Sí |  |  |  |
| pagado | VARCHAR | Sí |  |  |  |
| rechazado | CHAR | Sí |  |  |  |
| en_nd_proveedor | CHAR | Sí |  |  |  |
| tipo_cheque | VARCHAR | Sí |  |  |  |

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
| Info_Estadistica.frm | 3824 | SELECT | '                                         "Set reporte_flujo… |
| Info_Estadistica.frm | 3834 | SELECT | '                                         "Set reporte_flujo… |
| Info_Estadistica.frm | 4078 | SELECT | "Set reporte_flujofondos_temp.imp_chequemitido = (SELECT sum… |
| ml_consulta_indices.frm | 288 | SELECT | '        DataChequePropio.RecordSource = "SELECT chequepropi… |
| OrdenPago.frm | 7638 | SELECT | rs_chequepropio.Open "SELECT * FROM chequepropio WHERE ID = … |
| ABMChequeras.frm | 759 | SELECT | rs_ultimocheque.Open "SELECT max(NroCheque) as NCheque From … |
| Info_Banco.frm | 2914 | SELECT | "Set reporte_flujofondos_temp.imp_chequemitido = (SELECT sum… |
| Info_Banco.frm | 2924 | SELECT | "Set reporte_flujofondos_temp.imp_chequemitido = (SELECT sum… |
| PNotaDebCopia.frm | 2023 | SELECT | rs_chequepropio.Open "SELECT * FROM chequepropio WHERE ID = … |
| ConsultaComprobante.frm | 12374 | SELECT | rs_validacion.Open "SELECT * FROM ChequePropio WHERE Anulado… |
| ConsultaComprobante.frm | 12812 | SELECT | rs_chequepropio.Open "SELECT * FROM chequepropio WHERE Codig… |
| ConsultaComprobante.frm | 20595 | SELECT | rs_chequetercero.Open "SELECT * FROM chequepropio WHERE ID =… |
| ListaCheqEmitidos.frm | 909 | SELECT | sql_busqueda = " FROM chequepropio " & _ |
| ListaCheqEmitidos.frm | 921 | SELECT | sql_busqueda = " FROM chequepropio " & _ |
| ListaCheqEmitidos.frm | 939 | SELECT | sql_busqueda = " FROM chequepropio " & _ |
| ListaCheqEmitidos.frm | 952 | SELECT | sql_busqueda = " FROM chequepropio " & _ |
| ListaCheqEmitidos.frm | 965 | SELECT | sql_busqueda = " FROM chequepropio " & _ |
| CargaClearing.frm | 610 | SELECT | rs_chequeEmitido.Open "SELECT chequepropio.ID, chequepropio.… |
| trz_trazabilidadComp.frm | 4891 | SELECT | rs_chequepropio.Open "select * from chequepropio where chequ… |
| PNotaDeb.frm | 2117 | SELECT | rs_chequepropio.Open "SELECT * FROM chequepropio WHERE ID = … |
| CuentaProveedor.frm | 1422 | SELECT | '        rs_chequepropio.Open "select * from chequepropio wh… |
| CargaChequePropio.frm | 603 | SELECT | rs_chequepropio.Open "select * from chequepropio WHERE NroCh… |
| CargaChequePropio.frm | 848 | SELECT | rs_chequepropio.Open "select * from chequepropio WHERE " & _ |
| LibroBanco.frm | 3828 | SELECT | rs_chequeEmitido.Open "SELECT chequepropio.ID, chequepropio.… |
| Visualiza.bas | 7554 | SELECT | rs_chequepropio.Open "select * from chequepropio where chequ… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)