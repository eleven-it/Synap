# Tabla `banco`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodBanco | INT | No | ✓ |  |  |
| Nombre | VARCHAR | Sí |  |  |  |
| Domicilio | VARCHAR | Sí |  |  |  |
| CodProvincia | INT | Sí |  |  |  |
| Descubierto | INT | Sí |  |  |  |
| Email | VARCHAR | Sí |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| Telefono | TEXT | Sí |  |  |  |
| IDIva | INT | Sí |  |  |  |
| cuentaabierta | VARCHAR | Sí |  |  |  |
| codigo_bc | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| cod_bcra | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 2100 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT banco.Nombre as… |
| CargaBDeposito.frm | 2137 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT banco.Nombre as… |
| Visualiza_ReciboCobro.frm | 6960 | SELECT | rs_banco.Open "SELECT banco.Nombre,banco.CodBanco from banco… |
| Visualiza_ReciboCobro.frm | 9454 | JOIN | '        " INNER JOIN banco ON (banco.codbanco = cuenta_banc… |
| Visualiza_ReciboCobro.frm | 12815 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Visualiza_ReciboCobro.frm | 15874 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| ml_consulta_indices.frm | 291 | JOIN | "LEFT JOIN banco ON banco.CodBanco = chequepropio.Codbanco "… |
| ChequeTercero.frm | 2371 | JOIN | "LEFT JOIN banco ON banco.CodBanco=chequetercero.CodBanco " … |
| ChequeTercero.frm | 2410 | JOIN | "LEFT JOIN Banco as Origen ON ChequeTercero.CodBanco=Origen.… |
| ChequeTercero.frm | 2411 | JOIN | "LEFT JOIN Banco as Deposito ON ChequeTercero.CodBancoDep=De… |
| ChequeTercero.frm | 2449 | JOIN | "LEFT JOIN Banco as Origen ON ChequeTercero.CodBanco=Origen.… |
| ChequeTercero.frm | 2450 | JOIN | "LEFT JOIN Banco as Deposito ON ChequeTercero.CodBancoDep=De… |
| TPV.frm | 9985 | SELECT | rs_banco.Open "SELECT banco.Nombre,banco.CodBanco from banco… |
| Logi_Gestion2.frm | 9806 | JOIN | "LEFT JOIN banco ON (banco.CodBanco = chequetercero_temp.Cod… |
| CargaMovCaja.frm | 3301 | JOIN | " LEFT JOIN banco ON Banco.CodBanco = chequetercero.CodBanco… |
| ABMBanco.frm | 521 | SELECT | consulta = "SELECT * FROM banco WHERE CodBanco <> 1 and Nomb… |
| Logi_Gestion.frm | 11471 | JOIN | "LEFT JOIN banco ON (banco.CodBanco = chequetercero_temp.Cod… |
| OrdenPago.frm | 7597 | SELECT | rs_banco.Open "SELECT banco.Nombre,banco.CodBanco from banco… |
| OrdenPago.frm | 10861 | SELECT | rs_ultimocheque.Open "SELECT * FROM banco WHERE CodBanco = "… |
| OrdenPago.frm | 16508 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| ABMChequeras.frm | 869 | SELECT | DataBanco.RecordSource = "SELECT * FROM banco WHERE " & _ |
| ABMChequeras.frm | 1046 | SELECT | rs_banco.Open "select * from Banco where CodBanco = " & Data… |
| Exportacion.frm | 963 | JOIN | "LEFT JOIN banco ON (banco.CodBanco = librobanco.CodBanco)" … |
| Exportacion.frm | 1986 | SELECT | rs_banco.Open "select * from banco where CodBanco = " & rs_f… |
| Exportacion.frm | 5374 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & rs_f… |
| Exportacion.frm | 6247 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & rs_f… |
| Exportacion.frm | 6498 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & rs_f… |
| Exportacion.frm | 6930 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & rs_f… |
| Exportacion.frm | 10823 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & rs_f… |
| Exportacion.frm | 11363 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & rs_f… |
| Carga_Transferencia_REC_OP.frm | 777 | JOIN | '    " INNER JOIN banco ON (banco.codbanco = cuenta_banco.co… |
| ConsultaComprobante.frm | 30871 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| ListaCheqEmitidos.frm | 912 | JOIN | "LEFT JOIN banco ON banco.CodBanco = chequepropio.Codbanco "… |
| ListaCheqEmitidos.frm | 924 | JOIN | "LEFT JOIN banco ON banco.CodBanco = chequepropio.Codbanco "… |
| ListaCheqEmitidos.frm | 942 | JOIN | "LEFT JOIN banco ON banco.CodBanco = chequepropio.Codbanco "… |
| ListaCheqEmitidos.frm | 955 | JOIN | "LEFT JOIN banco ON banco.CodBanco = chequepropio.Codbanco "… |
| ListaCheqEmitidos.frm | 968 | JOIN | "LEFT JOIN banco ON banco.CodBanco = chequepropio.Codbanco "… |
| CargaTransBancaria.frm | 1036 | SELECT | DataBanco.RecordSource = "SELECT * FROM banco WHERE (CodBanc… |
| ABMUsuarios.frm | 985 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & rs_c… |
| CargaTarjetaC.frm | 666 | SELECT | DataBanco.RecordSource = "select * from banco order by Nombr… |
| ABMMercadoLibre.frm | 496 | SELECT | 'consulta = "SELECT * FROM banco WHERE CodBanco <> 1 and Nom… |
| ListaCheque3.frm | 874 | JOIN | '    " LEFT JOIN banco ON Banco.CodBanco = chequetercero.Cod… |
| ListaCheque3.frm | 875 | JOIN | '    " LEFT JOIN banco ON cliente.Codigo = chequetercero.Cod… |
| ListaCheque3.frm | 901 | JOIN | '    " LEFT JOIN banco ON Banco.CodBanco = chequetercero.Cod… |
| ListaCheque3.frm | 946 | JOIN | '                "LEFT JOIN banco ON (banco.codBanco = chequ… |
| ListaCheque3.frm | 1251 | JOIN | " LEFT JOIN banco ON Banco.CodBanco = chequetercero.CodBanco… |
| ListaCheque3.frm | 1288 | JOIN | " LEFT JOIN banco ON Banco.CodBanco = chequetercero.CodBanco… |
| ListaCheque3.frm | 1314 | JOIN | " LEFT JOIN banco ON Banco.CodBanco = chequetercero.CodBanco… |
| ReciboCobro.frm | 7456 | SELECT | rs_banco.Open "SELECT banco.Nombre,banco.CodBanco from banco… |
| ReciboCobro.frm | 17361 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| ChequeCliente.frm | 1357 | SELECT | consulta = "SELECT * FROM banco WHERE CodBanco <> 1 and anul… |
| Visualiza_ReciboCobroC.frm | 6726 | SELECT | rs_banco.Open "SELECT banco.Nombre,banco.CodBanco from banco… |
| TPV_2.frm | 9722 | SELECT | rs_banco.Open "SELECT banco.Nombre,banco.CodBanco from banco… |
| CargaBanco.frm | 431 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE Nombre = '" & Nombr… |
| CargaBanco.frm | 447 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE  CodBanco = 0", con… |
| CargaBanco.frm | 489 | SELECT | ABMChequera.DataBanco.RecordSource = "SELECT * FROM banco WH… |
| CargaBanco.frm | 501 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & ABMB… |
| Visualiza_OrdenPago.frm | 9429 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Visualiza_OrdenPago.frm | 11977 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| LibroBanco.frm | 1407 | SELECT | DataBanco.RecordSource = "SELECT * FROM banco WHERE (CodBanc… |
| CargaArticuloMLAsociacion.frm | 430 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE Nombre = '" & Nombr… |
| CargaArticuloMLAsociacion.frm | 446 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE  CodBanco = 0", con… |
| CargaArticuloMLAsociacion.frm | 475 | SELECT | ABMBanco.DataBanco.RecordSource = "SELECT * FROM banco WHERE… |
| CargaArticuloMLAsociacion.frm | 481 | SELECT | ABMChequera.DataBanco.RecordSource = "SELECT * FROM banco WH… |
| CargaArticuloMLAsociacion.frm | 493 | SELECT | rs_banco.Open "SELECT * FROM banco WHERE CodBanco = " & ABMB… |
| CargaArticuloMLAsociacion.frm | 520 | SELECT | ABMBanco.DataBanco.RecordSource = "SELECT * FROM banco WHERE… |
| Visualiza.bas | 6373 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Visualiza.bas | 6424 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Visualiza.bas | 7665 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Visualiza.bas | 7713 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Visualiza.bas | 20664 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Visualiza.bas | 21097 | JOIN | " INNER JOIN banco ON (banco.codbanco = cuenta_banco.codbanc… |
| Funciones.bas | 5390 | SELECT | rs_consulta.Open "SELECT codbanco,cuit FROM banco WHERE codb… |
| Funciones.bas | 6999 | SELECT | rs_consulta.Open "SELECT banco.CodBanco,banco.nombre FROM ba… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)