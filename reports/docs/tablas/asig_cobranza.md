# Tabla `asig_cobranza`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| ID | INT | No | ✓ |  |  |
| Fecha | DATE | Sí |  |  |  |
| tipo_asig | VARCHAR | Sí |  |  |  |

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
| NotaCredCon.frm | 2852 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| NotaCred_COPIA.frm | 3809 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| TPV.frm | 5576 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| TPV.frm | 6912 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| TPV.frm | 7088 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| NotaCred_SinCompO.frm | 4781 | SELECT | ''                    rs_asig_cobranza.Open "SELECT * FROM a… |
| PNotaDebCopia.frm | 4861 | SELECT | '                    rs_asig_cobranza.Open "SELECT * FROM as… |
| NotaCred_Importe.frm | 2448 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| NotaCredCopia.frm | 4381 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| ConsultaComprobante.frm | 6646 | SELECT | '                rs_asig_cob.Open "SELECT * FROM asig_cobran… |
| ConsultaComprobante.frm | 7084 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| ConsultaComprobante.frm | 8109 | SELECT | ''                rs_asig_cob.Open "SELECT * FROM asig_cobra… |
| ConsultaComprobante.frm | 8534 | SELECT | '                            rs_asig_cobranza.Open "SELECT *… |
| ConsultaComprobante.frm | 8852 | SELECT | '                    rs_asig_cob.Open "SELECT * FROM asig_co… |
| ConsultaComprobante.frm | 9383 | SELECT | rs_asig_cob.Open "SELECT * FROM asig_cobranza WHERE ID = " &… |
| ConsultaComprobante.frm | 10507 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| NotaDeb.frm | 2994 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| NotaCred.frm | 4525 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| PNotaDeb.frm | 5087 | SELECT | '                    rs_asig_cobranza.Open "SELECT * FROM as… |
| NotaDebCopia.frm | 2904 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| Visualiza_NotaCredCon.frm | 2740 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| TPV_2.frm | 6337 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |
| AsigCobranza.frm | 1135 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_cobranza WHERE ID … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)