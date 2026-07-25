# Tabla `talonarios`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Orden | INT | No | ✓ |  |  |
| TipoComprobante | VARCHAR | No |  |  |  |
| Nro | INT | Sí |  |  |  |
| CodSucursal | INT | No |  |  |  |
| NroInic | INT | No |  |  |  |
| NroFinal | INT | No |  |  |  |
| NroCAI | VARCHAR | No |  |  |  |
| FechaCAI | DATE | No |  |  |  |
| Detalle | VARCHAR | Sí |  |  |  |
| PV | INT | Sí |  |  |  |
| Habilitado | CHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_punto_venta | INT | Sí |  |  |  |
| id_comprobante | BIGINT | Sí |  |  |  |
| Nro_Credito | INT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 6300 | SELECT | rs_nro_rec.Open "SELECT * FROM talonarios WHERE id_punto_ven… |
| Erp_Carga_Parte_Diario.frm | 2459 | SELECT | rs_nro_fact.Open "SELECT * FROM talonarios WHERE id_punto_ve… |
| Visualiza_CargaMovStock.frm | 2931 | SELECT | rs_nro_comp.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2022 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2027 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2032 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2037 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2042 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2156 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2158 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2161 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2172 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2174 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2177 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2187 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2189 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2200 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2202 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2205 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2216 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2218 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2221 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2262 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredCon.frm | 2382 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3797 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3802 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3807 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3915 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3917 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3947 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3949 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3979 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 3981 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| FacturaB_COPIA.frm | 4021 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 1979 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 1984 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 1989 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 1994 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 1999 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2117 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2119 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2129 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2131 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2141 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2143 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2153 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2155 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2165 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2167 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2206 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCredDesc.frm | 2317 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| CargaTalonarios.frm | 1273 | SELECT | rs_talonario.Open "SELECT * FROM talonarios WHERE Orden =" &… |
| NotaCred_COPIA.frm | 2750 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2755 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2760 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2765 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2863 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2865 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2875 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2877 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2886 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2897 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2901 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2911 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 2947 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| NotaCred_COPIA.frm | 3046 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 5894 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 5896 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 5901 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8604 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8606 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8611 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8619 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8621 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8626 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8634 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8636 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8641 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8649 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| TPV.frm | 8651 | SELECT | rs_nro_fact.Open "select * from talonarios where id_punto_ve… |
| … | … | … | *(249 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)