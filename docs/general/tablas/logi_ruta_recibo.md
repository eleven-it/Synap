# Tabla `logi_ruta_recibo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_logi_ruta_recibo | DOUBLE | No | ✓ |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |
| codigo_movimiento_rec | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 12949 | SELECT | rs_rutaRec.Open "SELECT * FROM logi_ruta_recibo WHERE codigo… |
| Visualiza_ReciboCobro.frm | 12952 | UPDATE | conn.Execute "Update logi_ruta_recibo SET id_ruta = " & id_r… |
| Visualiza_ReciboCobro.frm | 12955 | INSERT | conn.Execute "INSERT INTO logi_ruta_recibo(id_ruta, codigo_m… |
| Logi_Gestion2.frm | 3468 | SELECT | "From logi_ruta_recibo " & _ |
| Logi_Gestion2.frm | 10912 | INSERT | '                        conn.Execute "INSERT INTO logi_ruta… |
| Logi_Gestion.frm | 4440 | INSERT | ''                        conn.Execute "INSERT INTO logi_rut… |
| Logi_Gestion.frm | 4480 | SELECT | "From logi_ruta_recibo " & _ |
| trz_trazabilidad.frm | 7773 | SELECT | "FROM logi_ruta_recibo " & _ |
| ConsultaComprobante.frm | 12197 | UPDATE | conn.Execute "UPDATE logi_ruta_recibo SET Anulado = 'Si' WHE… |
| ReciboCobro.frm | 7200 | INSERT | conn.Execute "INSERT INTO logi_ruta_recibo(id_ruta, codigo_m… |
| Visualiza_ReciboCobroC.frm | 12561 | SELECT | rs_rutaRec.Open "SELECT * FROM logi_ruta_recibo WHERE codigo… |
| Visualiza_ReciboCobroC.frm | 12564 | UPDATE | conn.Execute "Update logi_ruta_recibo SET id_ruta = " & id_r… |
| Visualiza_ReciboCobroC.frm | 12567 | INSERT | conn.Execute "INSERT INTO logi_ruta_recibo(id_ruta, codigo_m… |
| Visualiza.bas | 6721 | SELECT | "FROM logi_ruta_recibo " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)