# Tabla `punto_venta`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_punto_venta | INT | No | ✓ |  |  |
| nro_punto_venta | INT | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| lista_precio_pv | VARCHAR | Sí |  |  |  |
| fe_regimen | VARCHAR | Sí |  |  |  |
| ruta_reporte_comprobante | VARCHAR | Sí |  |  |  |
| ruta_certificado | VARCHAR | Sí |  |  |  |
| ruta_certificado_local | VARCHAR | Sí |  |  |  |
| cont | VARCHAR | Sí |  |  |  |
| selec | INT | Sí |  |  |  |
| bloquea_descuento_pie | VARCHAR | Sí |  |  |  |
| emp2 | VARCHAR | Sí |  |  |  |
| fe_regimen_tipo | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| detalle_pv | VARCHAR | Sí |  |  |  |
| emp3 | VARCHAR | Sí |  |  |  |
| tpv_venta_x_bulto | VARCHAR | Sí |  |  |  |
| activa_mp | VARCHAR | Sí |  |  |  |
| habilita_pv | VARBINARY | Sí |  |  |  |
| habilita_mp | VARBINARY | Sí |  |  |  |
| utiliza_regla_precio | VARCHAR | Sí |  |  |  |

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
| AsigUsrPv.frm | 744 | SELECT | "FROM punto_venta,sucursales WHERE " & _ |
| AsigUsrPv.frm | 757 | SELECT | "From punto_venta " & _ |
| AsigUsrPv.frm | 900 | SELECT | " FROM punto_venta ORDER BY punto_venta.id_punto_venta " |
| Visualiza_ReciboCobro.frm | 10813 | SELECT | rs_pv.Open "SELECT * FROM punto_venta WHERE nro_punto_venta … |
| Visualiza_ReciboCobro.frm | 12862 | SELECT | rs_pv.Open "SELECT * FROM punto_venta WHERE nro_punto_venta … |
| Visualiza_NotaCred.frm | 2548 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| Visualiza_NotaCred.frm | 2753 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| Visualiza_NotaCred.frm | 3069 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| Visualiza_NotaCred.frm | 4624 | SELECT | rs_pv.Open "SELECT * FROM punto_venta WHERE nro_punto_venta … |
| Visualiza_NotaCred.frm | 4901 | SELECT | rs_pv.Open "SELECT * FROM punto_venta WHERE nro_punto_venta … |
| CargaUsuario.frm | 2113 | SELECT | data_pv.RecordSource = "SELECT * FROM punto_venta ORDER BY p… |
| CargaUsuario.frm | 2406 | SELECT | data_pv.RecordSource = "SELECT * FROM punto_venta WHERE " & … |
| NotaCredCon.frm | 4438 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 4442 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 4700 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 4704 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 4956 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 5197 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 5430 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 5838 | SELECT | "From punto_venta " & _ |
| NotaCredCon.frm | 6327 | SELECT | rs_pv.Open "SELECT * FROM punto_venta WHERE nro_punto_venta … |
| NotaCredCon.frm | 7854 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 7867 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 7880 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 7893 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 7906 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8325 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8338 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8351 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8363 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8782 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8794 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8806 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 8818 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredCon.frm | 10263 | SELECT | rs_pv_elect.Open "select * from punto_venta where id_punto_v… |
| FacturaB_COPIA.frm | 6129 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 6469 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 6747 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 8564 | SELECT | '    data_pv.RecordSource = "SELECT punto_venta.id_punto_ven… |
| FacturaB_COPIA.frm | 8570 | SELECT | "From punto_venta " & _ |
| FacturaB_COPIA.frm | 10209 | SELECT | rs_pv.Open "SELECT * FROM punto_venta WHERE nro_punto_venta … |
| FacturaB_COPIA.frm | 13562 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 13950 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 14301 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 14749 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 15101 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 15395 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| FacturaB_COPIA.frm | 16510 | SELECT | rs_pv_elect.Open "select * from punto_venta where id_punto_v… |
| NotaCredDesc.frm | 1381 | SELECT | '    data_pv.RecordSource = "SELECT punto_venta.id_punto_ven… |
| NotaCredDesc.frm | 1387 | SELECT | "From punto_venta " & _ |
| NotaCredDesc.frm | 4898 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 5149 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 5403 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 5646 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 5890 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6131 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6144 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6157 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6170 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6183 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6605 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6618 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6631 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 6644 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 7065 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 7078 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 7091 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 7104 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCredDesc.frm | 8075 | SELECT | rs_pv_elect.Open "select * from punto_venta where id_punto_v… |
| NotaCred_COPIA.frm | 5104 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCred_COPIA.frm | 5356 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCred_COPIA.frm | 5728 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCred_COPIA.frm | 5964 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCred_COPIA.frm | 6886 | SELECT | '    data_pv.RecordSource = "SELECT punto_venta.id_punto_ven… |
| NotaCred_COPIA.frm | 6892 | SELECT | "From punto_venta " & _ |
| NotaCred_COPIA.frm | 7699 | SELECT | rs_pv.Open "SELECT * FROM punto_venta WHERE nro_punto_venta … |
| NotaCred_COPIA.frm | 10043 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCred_COPIA.frm | 10056 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCred_COPIA.frm | 10069 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| NotaCred_COPIA.frm | 10082 | SELECT | rs_informe.Open "select * FROM punto_venta WHERE id_punto_ve… |
| … | … | … | *(598 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| api_views.py | 592 | SELECT | FROM punto_venta |
| services/query_runner.py | 472 | JOIN | LEFT JOIN punto_venta pv ON pv.id_punto_venta = cc.id_pv |
| services/query_runner.py | 2241 | JOIN | LEFT JOIN punto_venta pv ON pv.id_punto_venta = cp.id_pv |
| services/query_runner.py | 3097 | JOIN | LEFT JOIN punto_venta pv ON pv.id_punto_venta = cp.id_pv |

[← Índice de tablas](../DB_INDICE_TABLAS.md)