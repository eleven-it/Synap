# Tabla `chequeterc_rec`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| NroCheque | DECIMAL | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| CodCliente | INT | Sí |  |  |  |
| CodProveedor | INT | Sí |  |  |  |
| Librador | VARCHAR | Sí |  |  |  |
| FechaEmision | DATE | Sí |  |  |  |
| FechaCobro | DATE | Sí |  |  |  |
| FechaVto | DATE | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| NroCompREC | VARCHAR | Sí |  |  |  |
| NroCompOP | VARCHAR | Sí |  |  |  |
| CUITLibrador | VARCHAR | Sí |  |  |  |
| Usado | VARCHAR | Sí |  |  |  |
| ID | DOUBLE | No | ✓ |  |  |
| CodigoMovimientoREC | DECIMAL | Sí |  |  |  |
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
| Visualiza_ReciboCobro.frm | 6999 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec where I… |
| TPV.frm | 7425 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE C… |
| CuentaCliente.frm | 2292 | SELECT | '        rs_chequeterc_rec.Open "SELECT * FROM chequeterc_re… |
| trz_trazabilidad.frm | 7394 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE c… |
| ConsultaComprobante.frm | 10939 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE C… |
| ConsultaComprobante.frm | 11600 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE C… |
| NotaDeb.frm | 14316 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE C… |
| ListaCheque3.frm | 1255 | JOIN | " LEFT JOIN chequeterc_rec ON chequeterc_rec.id = chequeterc… |
| ListaCheque3.frm | 1292 | JOIN | " LEFT JOIN chequeterc_rec ON chequeterc_rec.id = chequeterc… |
| NotaDebCopia.frm | 13967 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE C… |
| ReciboCobro.frm | 7490 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec where I… |
| Visualiza_ReciboCobroC.frm | 6765 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec where I… |
| TPV_2.frm | 6735 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE C… |
| Visualiza.bas | 6279 | SELECT | rs_chequeterc_rec.Open "SELECT * FROM chequeterc_rec WHERE c… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)