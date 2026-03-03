# Tabla `correo_log_envio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_correo_log_envio | DOUBLE | No | ✓ |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| fecha_envio | TIMESTAMP | No |  |  |  |
| remitente_correo | VARCHAR | Sí |  |  |  |
| destinatarios_correo | VARCHAR | Sí |  |  |  |
| asunto_correo | VARCHAR | Sí |  |  |  |
| mensaje_correo | VARCHAR | Sí |  |  |  |
| proceso | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| destinatarios_copia_correo | VARCHAR | Sí |  |  |  |

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
| CorreoEnvio2.frm | 3170 | INSERT | conn.Execute "INSERT INTO correo_log_envio " & _ |
| CorreoEnvio.frm | 1135 | INSERT | conn.Execute "INSERT INTO correo_log_envio " & _ |
| Correo_Log.frm | 589 | SELECT | "From correo_log_envio " & _ |
| Correo_Log.frm | 599 | SELECT | "From correo_log_envio " & _ |
| Correo_Log.frm | 666 | SELECT | "From correo_log_envio " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)