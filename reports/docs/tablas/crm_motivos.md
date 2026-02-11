# Tabla `crm_motivos`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_motivo | DOUBLE | No | ✓ |  |  |
| nombre_motivo | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |

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
| Crm_CargaLlamada.frm | 3318 | SELECT | "From crm_motivos " & _ |
| Crm_Info.frm | 1445 | SELECT | DataMotivo.RecordSource = "SELECT nombre_motivo FROM crm_mot… |
| Crm_AbmMotivo.frm | 396 | SELECT | "FROM Crm_motivos " & _ |
| Crm_AbmMotivo.frm | 423 | SELECT | "FROM crm_motivos " & _ |
| Crm_CargaMotivo.frm | 221 | INSERT | conn.Execute "INSERT INTO crm_motivos (nombre_motivo, anulad… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)