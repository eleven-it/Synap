# Tabla `otro_ingreso`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_oi | INT | No | ✓ |  |  |
| nombre_oi | VARCHAR | Sí |  |  |  |
| codigo_movimiento_rec | DECIMAL | Sí |  |  |  |
| importe_oi | DECIMAL | Sí |  |  |  |
| id_ingreso | DOUBLE | Sí |  |  |  |
| id_ingreso_abm | DOUBLE | Sí |  |  |  |
| id_mcp | DOUBLE | Sí |  |  |  |
| id_mcp_abm | DOUBLE | Sí |  |  |  |
| detalle_oi | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| fecha_oi | DATE | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7240 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE id_oi… |
| Visualiza_ReciboCobro.frm | 7361 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE id_oi… |
| trz_trazabilidad.frm | 7638 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE codig… |
| ConsultaComprobante.frm | 12123 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE codig… |
| ReciboCobro.frm | 7738 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE id_oi… |
| ReciboCobro.frm | 7859 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE id_oi… |
| Visualiza_ReciboCobroC.frm | 7006 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE id_oi… |
| Visualiza_ReciboCobroC.frm | 7127 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE id_oi… |
| Visualiza.bas | 6586 | SELECT | rs_otro_ingreso.Open "SELECT * FROM otro_ingreso WHERE codig… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)