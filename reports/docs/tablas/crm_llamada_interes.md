# Tabla `crm_llamada_interes`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_crm_li | BIGINT | No | ✓ |  |  |
| id_llamada | DOUBLE | Sí |  |  |  |
| id_interes | DOUBLE | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_llamada_interes | crm_intereses | Crm_CargaLlamada.frm | 4038 | sql_lista = "SELECT sql_no_cache * from crm_llamada_interes INNER JOIN crm_inter… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Crm_CargaLlamada.frm | 2695 | SELECT | conn.Execute "DELETE FROM crm_llamada_interes WHERE id_llama… |
| Crm_CargaLlamada.frm | 2695 | DELETE | conn.Execute "DELETE FROM crm_llamada_interes WHERE id_llama… |
| Crm_CargaLlamada.frm | 2702 | INSERT | sql_insertar = "INSERT INTO crm_llamada_interes (id_llamada,… |
| Crm_CargaLlamada.frm | 2972 | SELECT | 'sql_eliminar = "DELETE FROM crm_llamada_interes WHERE id_cr… |
| Crm_CargaLlamada.frm | 2972 | DELETE | 'sql_eliminar = "DELETE FROM crm_llamada_interes WHERE id_cr… |
| Crm_CargaLlamada.frm | 3158 | SELECT | 'sql_eliminar = "DELETE FROM crm_llamada_interes WHERE id_cr… |
| Crm_CargaLlamada.frm | 3158 | DELETE | 'sql_eliminar = "DELETE FROM crm_llamada_interes WHERE id_cr… |
| Crm_CargaLlamada.frm | 4038 | SELECT | sql_lista = "SELECT sql_no_cache * from crm_llamada_interes … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)