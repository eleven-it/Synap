# Tabla `en_chofer`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_chofer | BIGINT | No | ✓ |  |  |
| codigo_proveedor | BIGINT | Sí |  |  |  |
| nombre_chofer | VARCHAR | Sí |  |  |  |
| tipo_documento | VARCHAR | Sí |  |  |  |
| nro_documento | VARCHAR | Sí |  |  |  |
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
| En_ABM_Chofer.frm | 465 | SELECT | consulta = "SELECT * FROM en_chofer WHERE  Nombre_chofer LIK… |
| En_ABM_Chofer.frm | 466 | SELECT | consulta = "SELECT id_en_chofer,p.Nombre as proveedor,codigo… |
| ConsultaComprobante.frm | 3458 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = p.id_en_cho… |
| ConsultaComprobante.frm | 3483 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = p.id_en_cho… |
| ConsultaComprobante.frm | 3614 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = v.id_en_cho… |
| ConsultaComprobante.frm | 3642 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = v.id_en_cho… |
| En_Info.frm | 3741 | SELECT | " FROM en_chofer AS ch" & _ |
| En_Info.frm | 3785 | SELECT | " FROM en_chofer" & _ |
| En_Info.frm | 3941 | SELECT | " FROM en_chofer AS ch" & _ |
| En_Info.frm | 3947 | SELECT | " FROM en_chofer AS ch" & _ |
| En_Info.frm | 3965 | SELECT | " FROM en_chofer AS ch" & _ |
| En_Carga_Clasificacion_Pesaje.frm | 1488 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = p.id_en_cho… |
| En_Pesajes_Pendientes.frm | 640 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = p.id_en_cho… |
| En_Carga_Chofer.frm | 511 | SELECT | rs_banco.Open "SELECT * FROM en_chofer WHERE nro_documento =… |
| En_Carga_Chofer.frm | 527 | SELECT | rs_banco.Open "SELECT * FROM en_chofer WHERE  id_en_chofer =… |
| En_Carga_Chofer.frm | 550 | SELECT | En_ABM_Chofer.DataChofer.RecordSource = "SELECT id_en_chofer… |
| En_Carga_Chofer.frm | 565 | SELECT | rs_banco.Open "SELECT * FROM en_chofer WHERE id_en_chofer = … |
| En_Carga_Chofer.frm | 587 | SELECT | En_ABM_Chofer.DataChofer.RecordSource = "SELECT id_en_chofer… |
| En_Carga_Pesaje.frm | 6494 | SELECT | " FROM en_chofer AS ch" & _ |
| En_Liquidacion_Vales.frm | 2426 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = v.id_en_cho… |
| En_Liquidacion_Vales.frm | 2606 | SELECT | " FROM en_chofer AS ch" & _ |
| En_Liquidacion_Vales.frm | 2650 | SELECT | " FROM en_chofer" & _ |
| En_Liquidacion_Vales.frm | 2693 | JOIN | " LEFT JOIN en_chofer AS ch ON ch.id_en_chofer = v.id_en_cho… |
| En_Carga_Vale.frm | 5424 | SELECT | " FROM en_chofer AS ch" & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)