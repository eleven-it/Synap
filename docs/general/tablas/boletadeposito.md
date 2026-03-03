# Tabla `boletadeposito`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| NroBoleta | VARCHAR | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| Fecha | DATETIME | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| CodCuenta | INT | No |  |  |  |
| ID | BIGINT | No | ✓ |  |  |
| TipoB | INT | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| detalle | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 1370 | SELECT | rs_boletadeposito.Open "SELECT * FROM boletadeposito WHERE I… |
| CargaBDeposito.frm | 1557 | SELECT | rs_boletadeposito.Open "SELECT * FROM boletadeposito WHERE C… |
| LibroBanco.frm | 1994 | SELECT | rs_boletadeposito.Open "SELECT * FROM boletadeposito WHERE I… |
| LibroBanco.frm | 2180 | SELECT | rs_boletadeposito.Open "SELECT * FROM boletadeposito WHERE I… |
| LibroBanco.frm | 4071 | SELECT | '        rs_consulta_bd.Open "SELECT * FROM boletadeposito W… |
| LibroBanco.frm | 4072 | SELECT | rs_consulta_bd.Open "SELECT * FROM boletadeposito WHERE codi… |
| Visualiza.bas | 23390 | SELECT | rs_comprobante.Open "SELECT boletadeposito.* FROM boletadepo… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)