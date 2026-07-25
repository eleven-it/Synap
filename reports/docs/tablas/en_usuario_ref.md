# Tabla `en_usuario_ref`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_usuario_ref | DOUBLE | No | ✓ |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| id_en_detalle_abm | DOUBLE | Sí |  |  |  |
| nombre_usuario | VARCHAR | Sí |  |  |  |
| permiso | VARCHAR | Sí |  |  |  |

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
| En_Carga_UsuRef.frm | 749 | SELECT | rs.Open "SELECT * FROM en_usuario_ref WHERE id_en_detalle_ab… |
| En_Carga_UsuRef.frm | 766 | INSERT | conn.Execute "INSERT INTO en_usuario_ref (id_en_detalle_abm,… |
| En_Carga_UsuRef.frm | 798 | SELECT | conn.Execute "DELETE FROM en_usuario_ref WHERE id_usuario_re… |
| En_Carga_UsuRef.frm | 798 | DELETE | conn.Execute "DELETE FROM en_usuario_ref WHERE id_usuario_re… |
| En_Carga_UsuRef.frm | 972 | SELECT | DataLista.RecordSource = "SELECT * FROM en_usuario_ref " & _ |
| En_GestionOE.frm | 901 | SELECT | rs_Ref.Open "SELECT * FROM en_usuario_ref ", conn, adOpenDyn… |
| En_GestionOE.frm | 916 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |
| En_GestionOE.frm | 921 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |
| En_GeneraPOE.frm | 2545 | SELECT | rs_Ref.Open "SELECT * FROM en_usuario_ref ", conn, adOpenDyn… |
| En_GeneraPOE.frm | 2556 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |
| En_GeneraPOE.frm | 2561 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |
| En_CargaOE_Ref.frm | 1044 | SELECT | rs_Ref.Open "SELECT * FROM en_usuario_ref WHERE id_usuario =… |
| En_CargaOE_Ref.frm | 1057 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |
| En_CargaOE_Ref.frm | 1063 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |
| En_CargaOE_Ref.frm | 1073 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |
| En_CargaOE_Ref.frm | 1079 | JOIN | "LEFT JOIN en_usuario_ref ON (en_usuario_ref.id_en_detalle_a… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)