# Tabla `en_etapa_ref`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_etapa_ref | DOUBLE | No | ✓ |  |  |
| id_en_detalle_abm | DOUBLE | Sí |  |  |  |
| estado_en_detalle | VARCHAR | Sí |  |  |  |

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
| En_GestionOE.frm | 970 | SELECT | rs_etapa.Open "SELECT * FROM en_etapa_ref " & _ |
| En_Carga_EtapaRef.frm | 518 | SELECT | rs.Open "SELECT * FROM en_etapa_ref WHERE id_en_detalle_abm … |
| En_Carga_EtapaRef.frm | 535 | INSERT | conn.Execute "INSERT INTO en_etapa_ref (id_en_detalle_abm, e… |
| En_Carga_EtapaRef.frm | 565 | SELECT | conn.Execute "DELETE FROM en_etapa_ref WHERE id_etapa_ref = … |
| En_Carga_EtapaRef.frm | 565 | DELETE | conn.Execute "DELETE FROM en_etapa_ref WHERE id_etapa_ref = … |
| En_Carga_EtapaRef.frm | 725 | SELECT | DataLista.RecordSource = "SELECT * FROM en_etapa_ref " & _ |
| En_CargaOE_Ref.frm | 1126 | SELECT | rs_etapa.Open "SELECT * FROM en_etapa_ref " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)