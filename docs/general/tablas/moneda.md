# Tabla `moneda`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_moneda | INT | No | ✓ |  |  |
| nombre | VARCHAR | No |  |  |  |
| compra | DECIMAL | Sí |  |  |  |
| venta | DECIMAL | Sí |  |  |  |
| variacion | DOUBLE | Sí |  |  |  |
| cierre | DECIMAL | Sí |  |  |  |
| respecto | INT | Sí |  |  |  |
| fecha | DATE | No |  |  |  |
| hora | TIME | No |  |  |  |

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
| Sup_importacion_tablas.frm | 6094 | SELECT | DataMoneda.RecordSource = "SELECT * FROM moneda ORDER BY nom… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)