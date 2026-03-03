# Tabla `crm_llamada_log`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_llamada_log | DOUBLE | No | ✓ |  |  |
| id_llamada | DOUBLE | Sí |  |  |  |
| fecha_llamada | TIMESTAMP | No |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_cliente_potencial | DOUBLE | Sí |  |  |  |
| id_vendedor | DOUBLE | Sí |  |  |  |
| tipo_cli | VARCHAR | Sí |  |  |  |
| desc_requerimiento | VARCHAR | Sí |  |  |  |
| fecha_prox_llamada | DATE | Sí |  |  |  |
| hora_prox_llamada | TIME | Sí |  |  |  |
| desc_accion | VARCHAR | Sí |  |  |  |
| origen | VARCHAR | Sí |  |  |  |
| llamada_efectuada | VARCHAR | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| motivo | VARCHAR | Sí |  |  |  |
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
| Crm_CargaLlamada.frm | 2720 | INSERT | conn.Execute "INSERT INTO crm_llamada_log(id_llamada, id_usu… |
| Crm_Historial.frm | 456 | SELECT | "FROM crm_llamada_log " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)