# Tabla `boletacheque`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodBoleta | BIGINT | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| NroCheque3 | VARCHAR | Sí |  |  |  |
| CodBanco3 | VARCHAR | Sí |  |  |  |
| ID | BIGINT | No | ✓ |  |  |
| CodCheque3 | DOUBLE | Sí |  |  |  |
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
| CargaBDeposito.frm | 1578 | SELECT | rs_boletaCheque.Open "SELECT * FROM boletacheque WHERE ID = … |
| CargaBDeposito.frm | 2061 | SELECT | rs_boletadeposito.Open "SELECT * FROM boletacheque WHERE cod… |
| LibroBanco.frm | 2185 | SELECT | rs_boletaCheque.Open "SELECT * FROM boletacheque WHERE CodBo… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)