# Tabla `reporte_comprobante`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_reporte_comprobante | INT | No | ✓ |  |  |
| nombre_reporte_comprobante | VARCHAR | Sí |  |  |  |
| nombre_impresora | VARCHAR | Sí |  |  |  |
| numero_copias | INT | Sí |  |  |  |
| detalle_comprobante | MEDIUMTEXT | Sí |  |  |  |
| puerto_impresora | VARCHAR | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| id_punto_venta | INT | Sí |  |  |  |
| id_imp_fiscal | INT | Sí |  |  |  |
| baudios_imp_fiscal | VARCHAR | Sí |  |  |  |
| tipo_conexion_imp_fiscal | VARCHAR | Sí |  |  |  |
| ip_imp_fiscal | VARCHAR | Sí |  |  |  |
| tipo_impresora | VARCHAR | Sí |  |  |  |
| tipo_hoja_crystal | INT | Sí |  |  |  |
| tipo_hoja_crystal_desc | VARCHAR | Sí |  |  |  |
| tipo_hoja_fiscal | VARCHAR | Sí |  |  |  |
| tipo_hoja_ancho_fiscal | VARCHAR | Sí |  |  |  |
| tipo_hoja_fiscal_desc | VARCHAR | Sí |  |  |  |
| detalle_comprobante2 | MEDIUMTEXT | Sí |  |  |  |
| detalle_comprobante3 | MEDIUMTEXT | Sí |  |  |  |
| detalle_comprobante4 | MEDIUMTEXT | Sí |  |  |  |
| hoja_orientacion_crystal | INT | Sí |  |  |  |
| hoja_orientacion_crystal_desc | VARCHAR | Sí |  |  |  |
| id_comprobante | BIGINT | Sí |  |  |  |

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
| Visualiza_NotaCred.frm | 2616 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| Visualiza_NotaCred.frm | 2821 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| Visualiza_NotaCred.frm | 3137 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 1935 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 1939 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 4554 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 4811 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 5057 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 5295 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 5520 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8090 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8147 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8204 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8261 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8544 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8601 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8658 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8715 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 8995 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 9052 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 9109 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredCon.frm | 9166 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 3757 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 6303 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 6616 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 6833 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 13847 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 14225 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 14574 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 15004 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 15324 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| FacturaB_COPIA.frm | 15614 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 1886 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 5008 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 5259 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 5504 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 5752 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 5980 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6367 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6424 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6481 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6538 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6825 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6882 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6939 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 6996 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 7286 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 7343 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 7400 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCredDesc.frm | 7457 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 2705 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 5216 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 5460 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 5823 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 6075 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10267 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10324 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10381 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10438 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10710 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10767 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10824 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 10879 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 11162 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 11219 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 11276 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| NotaCred_COPIA.frm | 11331 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| CargaSucursal.frm | 1142 | SELECT | '        rs_reporte_comprobante.Open "SELECT * FROM reporte_… |
| Visualiza_TPV.frm | 7881 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| Visualiza_TPV.frm | 8071 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 5852 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 8556 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 17491 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 17734 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 18111 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 23605 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 23667 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 23726 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 24211 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| TPV.frm | 24273 | SELECT | rs_informe.Open "select * FROM reporte_comprobante WHERE id_… |
| … | … | … | *(258 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)