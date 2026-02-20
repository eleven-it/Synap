# Tabla `asig_pago`

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
| PNotaCred.frm | 3448 | SELECT | rs_asig_pago.Open "SELECT * FROM asig_pago WHERE ID = 1", co… |
| PNotaCred.frm | 3694 | SELECT | '                                    rs_asig_cobranza.Open "… |
| Visualiza_PNotaCred_Importe.frm | 2311 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_pago WHERE ID = 1"… |
| Visualiza_PNotaCredDev.frm | 2979 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_pago WHERE ID = 1"… |
| AsigPago.frm | 1095 | SELECT | rs_asig_pago.Open "SELECT * FROM asig_pago WHERE ID = 1", co… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2176 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_pago WHERE ID = 1"… |
| ConsultaComprobante.frm | 18832 | SELECT | rs_asig_pago.Open "SELECT * FROM asig_pago WHERE ID = " & rs… |
| ConsultaComprobante.frm | 19193 | SELECT | rs_asig_pago.Open "SELECT * FROM asig_pago WHERE ID = " & rs… |
| ConsultaComprobante.frm | 19629 | SELECT | '            rs_asig_pago.Open "SELECT * FROM asig_pago WHER… |
| ConsultaComprobante.frm | 19843 | SELECT | rs_asig_pago.Open "SELECT * FROM asig_pago WHERE ID = " & rs… |
| PNotaCred_Importe.frm | 2305 | SELECT | rs_asig_pago.Open "SELECT * FROM asig_pago WHERE ID = 1", co… |
| PNotaCred_Importe.frm | 2555 | SELECT | '                                    rs_asig_cobranza.Open "… |
| PNotaCredCopia.frm | 3363 | SELECT | rs_asig_pago.Open "SELECT * FROM asig_pago WHERE ID = 1", co… |
| PNotaCredCopia.frm | 3609 | SELECT | '                                    rs_asig_cobranza.Open "… |
| Visualiza_PNotaCredDevC.frm | 3108 | SELECT | rs_asig_cobranza.Open "SELECT * FROM asig_pago WHERE ID = 1"… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)