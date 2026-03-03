# Tabla `transporte`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_transporte | INT | No | ✓ |  |  |
| nombre_transporte | VARCHAR | No |  |  |  |
| tel_transporte | VARCHAR | Sí |  |  |  |
| email_transporte | VARCHAR | Sí |  |  |  |
| calle | VARCHAR | Sí |  |  |  |
| nrocalle | VARCHAR | Sí |  |  |  |
| idDistrito | INT | Sí |  |  |  |
| idProvincia | INT | Sí |  |  |  |
| idDepartamento | INT | Sí |  |  |  |
| dpto | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | No |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| patente | VARCHAR | Sí |  |  |  |

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
| Info_Stock.frm | 11722 | SELECT | DataTransporte.RecordSource = "select * from transporte wher… |
| CargaTransporte.frm | 788 | SELECT | rs_tr.Open "SELECT * FROM transporte WHERE Nombre_transporte… |
| CargaTransporte.frm | 804 | SELECT | rs_tr.Open "SELECT * FROM transporte WHERE  id_transporte = … |
| CargaTransporte.frm | 835 | SELECT | ABMTransporte.DataTR.RecordSource = "SELECT * from transport… |
| CargaTransporte.frm | 847 | SELECT | rs_tr.Open "SELECT * FROM transporte WHERE id_transporte = "… |
| Logi_Gestion2.frm | 5303 | SELECT | DataTransporte.RecordSource = "select * From transporte wher… |
| Logi_Gestion2.frm | 8023 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Logi_Gestion2.frm | 8128 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Logi_Gestion2.frm | 8232 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Visualiza_Pedido.frm | 6369 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| Visualiza_Pedido.frm | 10701 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| Logi_Gestion.frm | 6535 | SELECT | DataTransporte.RecordSource = "select * From transporte wher… |
| Logi_Gestion.frm | 9539 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Logi_Gestion.frm | 9560 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Logi_Gestion.frm | 9668 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Logi_Gestion.frm | 9775 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Carga_DatosAdicionales.frm | 1626 | SELECT | DataTransporte.RecordSource = "select * from transporte wher… |
| Carga_DatosAdicionales.frm | 2847 | JOIN | ''                  "LEFT JOIN transporte ON (transporte.id_… |
| Stock_Control.frm | 2917 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| ListadoFacturas.frm | 910 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| ListadoFacturas.frm | 1027 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_prep.frm | 3997 | SELECT | DataTransporte.RecordSource = "select * From transporte wher… |
| Remito.frm | 6193 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Remito.frm | 6536 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Remito.frm | 8254 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| Remito.frm | 8580 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| Pedido_Avanzado.frm | 3337 | SELECT | DataTransporte.RecordSource = "select * from transporte wher… |
| Pedido_Avanzado.frm | 4253 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_Avanzado.frm | 4525 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_Avanzado.frm | 4774 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_Avanzado.frm | 6734 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_Avanzado.frm | 9615 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_Avanzado.frm | 11069 | JOIN | '                                        "LEFT JOIN transpor… |
| Pedido_Avanzado.frm | 11540 | JOIN | '                                    "LEFT JOIN transporte O… |
| Pedido_Avanzado.frm | 13087 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_Avanzado.frm | 13207 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido_Avanzado.frm | 13353 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Pedido.frm | 7599 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| Visualiza_RemitoCopia.frm | 4956 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| Visualiza_RemitoCopia.frm | 5088 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| ConsultaComprobante.frm | 14633 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| ConsultaComprobante.frm | 15227 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| ConsultaComprobante.frm | 16890 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| ConsultaComprobante.frm | 17840 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| ConsultaComprobante.frm | 26944 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| ConsultaComprobante.frm | 31977 | SELECT | rs_transporte.Open "SELECT nombre_transporte FROM transporte… |
| ConsultaComprobante.frm | 32901 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| ConsultaComprobante.frm | 35194 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| Logi_OrdenRuta.frm | 959 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| ABMTransporte.frm | 504 | SELECT | DataTR.RecordSource = "SELECT * FROM transporte WHERE Nombre… |
| ABMTransporte.frm | 542 | SELECT | DataTR.RecordSource = "select * from transporte order by Nom… |
| Lista_Comp_Gral.frm | 2871 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 3429 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 3817 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 5403 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 5874 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 6435 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 9135 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 9594 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 10043 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 11107 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 11479 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 12411 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 12767 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Gral.frm | 13134 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Fact.frm | 5429 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Fact.frm | 6132 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Fact.frm | 6723 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Fact.frm | 7720 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Fact.frm | 8329 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Fact.frm | 9030 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Lista_Comp_Fact.frm | 9645 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| Visualiza_Remito.frm | 4993 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| Visualiza_Remito.frm | 5125 | SELECT | 'DataTransporte.RecordSource = "select * from transporte whe… |
| Principal.frm | 9803 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| Principal.frm | 10515 | SELECT | rs_transporte.Open "SELECT * FROM transporte WHERE id_transp… |
| ListaFacturasNC.frm | 1563 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| ListaFacturasNC.frm | 2580 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| ListaFacturasNC.frm | 3279 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| ListaFacturasNC.frm | 3921 | JOIN | "LEFT JOIN transporte ON (transporte.id_transporte = cliente… |
| … | … | … | *(17 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)