# Tabla `otro_egreso`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_oe | INT | No | ✓ |  |  |
| nombre_oe | VARCHAR | Sí |  |  |  |
| codigo_movimiento_op | DECIMAL | Sí |  |  |  |
| tipo_oe | VARCHAR | Sí |  |  |  |
| importe_oe | DECIMAL | Sí |  |  |  |
| id_impuesto | INT | Sí |  |  |  |
| id_impuesto_detalle | DOUBLE | Sí |  |  |  |
| id_gasto | INT | Sí |  |  |  |
| id_deuda_abm | INT | Sí |  |  |  |
| id_deuda | DOUBLE | Sí |  |  |  |
| detalle_oe | VARCHAR | Sí |  |  |  |
| fecha_oe | DATE | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_percepcion | DOUBLE | Sí |  |  |  |
| importe_percepcion | DECIMAL | Sí |  |  |  |
| id_sucursal | BIGINT | Sí |  |  |  |
| id_cierre_caja | BIGINT | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2719 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2725 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2774 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2791 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2851 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2857 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2872 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2878 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| PNotaCred.frm | 3223 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| Info_Estadistica.frm | 2719 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Info_Estadistica.frm | 2725 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Info_Estadistica.frm | 2774 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Info_Estadistica.frm | 2791 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| NotaCredCon.frm | 3103 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| CargaMovCaja.frm | 2189 | UPDATE | conn.Execute "UPDATE otro_egreso " & _ |
| OrdenPago.frm | 7928 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| PNotaDebCopia.frm | 5351 | UPDATE | '                    conn.Execute "UPDATE otro_egreso SET an… |
| Exportacion.frm | 6433 | SELECT | "FROM otro_egreso " & _ |
| Exportacion.frm | 6805 | SELECT | "FROM otro_egreso " & _ |
| Exportacion.frm | 6873 | SELECT | "FROM otro_egreso " & _ |
| CargaGastoBancario.frm | 1045 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| PFactura.frm | 4701 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| ConsultaComprobante.frm | 13106 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE codigo_… |
| ConsultaComprobante.frm | 30298 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE codigo_… |
| ConsultaComprobante.frm | 30933 | UPDATE | conn.Execute "UPDATE otro_egreso SET anulado = 'Si' " & _ |
| CargaLiquidacionTC.frm | 1784 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| NotaDeb.frm | 3631 | UPDATE | conn.Execute "UPDATE otro_egreso SET anulado = 'Si' " & _ |
| Visualiza_PFactura_Copia.frm | 3723 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| trz_trazabilidadComp.frm | 5013 | SELECT | rs_otro_egreso.Open "select * from otro_egreso where codigo_… |
| Visualiza_OrdenPagoC.frm | 9100 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE codigo_… |
| PNotaDeb.frm | 5577 | UPDATE | '                    conn.Execute "UPDATE otro_egreso SET an… |
| PNotaCredCopia.frm | 3147 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| NotaDebCopia.frm | 3541 | UPDATE | conn.Execute "UPDATE otro_egreso SET anulado = 'Si' " & _ |
| CargaDeudaBancaria.frm | 951 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| CargaDNF_Caja.frm | 946 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| Erp_Info.frm | 2851 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Erp_Info.frm | 2857 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Erp_Info.frm | 2872 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Erp_Info.frm | 2878 | JOIN | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Visualiza_PFacturaCopia2.frm | 3862 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| Visualiza_PFactura.frm | 3936 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| Visualiza_NotaCredCon.frm | 2991 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE id_oe =… |
| Visualiza_OrdenPago.frm | 9507 | SELECT | rs_otro_egreso.Open "SELECT * FROM otro_egreso WHERE codigo_… |
| LibroBanco.frm | 3455 | SELECT | rs_otroegreso.Open "SELECT * from otro_egreso where codigo_m… |
| LibroBanco.frm | 4498 | SELECT | rs_Oegreso.Open "SELECT * from otro_egreso where codigo_movi… |
| Visualiza.bas | 7766 | SELECT | rs_otro_egreso.Open "select * from otro_egreso where codigo_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)