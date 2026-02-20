# Tabla `retencion_juridic_convenio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_juridic_convenio | DOUBLE | No | ✓ |  |  |
| nombre_juridiccion | VARCHAR | Sí |  |  |  |
| cod_juridiccion | INT | Sí |  |  |  |
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
| CargaRetCli.frm | 916 | SELECT | data_juridiccion.RecordSource = "select * from retencion_jur… |
| Exportacion.frm | 874 | SELECT | rs_juridic_convenio.Open "SELECT * FROM retencion_juridic_co… |
| Exportacion.frm | 881 | JOIN | "LEFT JOIN retencion_juridic_convenio ON (retencion_juridic_… |
| Exportacion.frm | 911 | SELECT | rs_juridic_convenio.Open "SELECT * FROM retencion_juridic_co… |
| Exportacion.frm | 924 | JOIN | "LEFT JOIN retencion_juridic_convenio ON (retencion_juridic_… |
| Exportacion.frm | 1179 | JOIN | " LEFT JOIN retencion_juridic_convenio ON (retencion_juridic… |
| Exportacion.frm | 11712 | JOIN | " LEFT JOIN retencion_juridic_convenio ON (retencion_juridic… |
| Exportacion.frm | 11828 | JOIN | "LEFT JOIN retencion_juridic_convenio ON (retencion_juridic_… |
| Exportacion.frm | 12062 | JOIN | " LEFT JOIN retencion_juridic_convenio ON (retencion_juridic… |
| Exportacion.frm | 12215 | JOIN | " LEFT JOIN retencion_juridic_convenio ON (retencion_juridic… |
| Exportacion.frm | 12426 | JOIN | " LEFT JOIN retencion_juridic_convenio ON (retencion_juridic… |
| CargaRetProv.frm | 619 | SELECT | data_jurisdiccion.RecordSource = "SELECT * FROM retencion_ju… |
| CargaPercepcionesCliTipo.frm | 868 | SELECT | data_jurisdiccion.RecordSource = "SELECT * FROM retencion_ju… |
| ABMPercepcionesCliTipo.frm | 428 | JOIN | '                                     " LEFT JOIN retencion_… |
| ABMPercepcionesCliTipo.frm | 655 | JOIN | " LEFT JOIN retencion_juridic_convenio ON (retencion_juridic… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)