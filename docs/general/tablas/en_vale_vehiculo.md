# Tabla `en_vale_vehiculo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_vale_vehiculo | BIGINT | No | ✓ |  |  |
| id_tara_temporada | BIGINT | Sí |  |  |  |
| patente_vehiculo | VARCHAR | Sí |  |  |  |
| tara_temporada | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_vale | BIGINT | Sí |  |  |  |
| id_precio_zona | BIGINT | Sí |  |  |  |
| precio_kilo | DECIMAL | Sí |  |  |  |
| total_tara_bines | DECIMAL | Sí |  |  |  |
| bruto_vehiculo | DECIMAL | Sí |  |  |  |
| neto_vehiculo | DECIMAL | Sí |  |  |  |
| importe_neto_precio | DECIMAL | Sí |  |  |  |
| nombre_vehiculo | VARCHAR | Sí |  |  |  |

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
| ConsultaComprobante.frm | 5173 | SELECT | rs_vehiculo_vale.Open "SELECT * FROM en_vale_vehiculo WHERE … |
| ConsultaComprobante.frm | 5445 | SELECT | rs_vehiculo_vale.Open "SELECT * FROM en_vale_vehiculo WHERE … |
| En_Carga_Pesaje.frm | 5428 | SELECT | rs_vale_vehiculo.Open "SELECT * FROM en_vale_vehiculo WHERE … |
| En_Carga_Pesaje.frm | 5458 | SELECT | "FROM en_vale_vehiculo AS vv " & _ |
| En_Carga_Vale.frm | 4042 | SELECT | " FROM en_vale_vehiculo AS vv " & _ |
| En_Carga_Vale.frm | 4522 | SELECT | rs_vale_vehiculo.Open "SELECT * FROM en_vale_vehiculo WHERE … |
| En_Carga_Vale.frm | 4752 | SELECT | "FROM en_vale_vehiculo AS vv " & _ |
| En_Carga_Vale.frm | 5777 | SELECT | " FROM en_vale_vehiculo AS vv " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)