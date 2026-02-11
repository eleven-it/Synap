# Tabla `crm_articulo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_crm | DOUBLE | No | ✓ |  |  |
| id_llamada | DOUBLE | Sí |  |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| oportunidad | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_articulo | articulo | Crm_CargaLlamada.frm | 4162 | sql_lista = "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.id_… |
| crm_articulo | articulo | Crm_Presupuesto_Llamada.frm | 681 | 'SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.id_articulo = a… |
| crm_articulo | stockp | Crm_Presupuesto_Llamada.frm | 681 | 'SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.id_articulo = a… |
| crm_articulo | articulo | Crm_Presupuesto_Llamada.frm | 682 | rs_articulo.Open "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articul… |
| crm_articulo | articulo | Crm_Presupuesto_Llamada.frm | 692 | rs_stock.Open "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.i… |
| crm_articulo | stockp | Crm_Presupuesto_Llamada.frm | 692 | rs_stock.Open "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.i… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Crm_CargaLlamada.frm | 2438 | INSERT | '            conn.Execute "INSERT INTO crm_articulo(id_llama… |
| Crm_CargaLlamada.frm | 2489 | SELECT | '            conn.Execute "DELETE crm_articulo.* FROM crm_ar… |
| Crm_CargaLlamada.frm | 2495 | INSERT | '            conn.Execute "INSERT INTO crm_articulo(id_llama… |
| Crm_CargaLlamada.frm | 2512 | SELECT | conn.Execute "DELETE FROM crm_articulo WHERE id_llamada = " … |
| Crm_CargaLlamada.frm | 2512 | DELETE | conn.Execute "DELETE FROM crm_articulo WHERE id_llamada = " … |
| Crm_CargaLlamada.frm | 2519 | INSERT | sql_insertar = "INSERT INTO crm_articulo (id_llamada, id_art… |
| Crm_CargaLlamada.frm | 2563 | SELECT | '        sql_articulos = "SELECT * FROM articulo WHERE idArt… |
| Crm_CargaLlamada.frm | 4162 | SELECT | sql_lista = "SELECT * FROM crm_articulo INNER JOIN articulo … |
| Crm_AbmLlamada.frm | 1219 | SELECT | '                    "From crm_articulo " & _ |
| Crm_AbmLlamada.frm | 1232 | SELECT | '                    "From crm_articulo " & _ |
| Crm_Presupuesto_Llamada.frm | 681 | SELECT | 'SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_arti… |
| Crm_Presupuesto_Llamada.frm | 682 | SELECT | rs_articulo.Open "SELECT * FROM crm_articulo INNER JOIN arti… |
| Crm_Presupuesto_Llamada.frm | 692 | SELECT | rs_stock.Open "SELECT * FROM crm_articulo INNER JOIN articul… |
| Funciones.bas | 13119 | SELECT | rs_articulos.Open "SELECT * FROM articulo WHERE idArt IN (SE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)