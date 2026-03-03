# Tabla `articulo_promo_intervalo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_promo_intervalo | DOUBLE | No | ✓ |  |  |
| desde_cantidad | DOUBLE | Sí |  |  |  |
| hasta_cantidad | DOUBLE | Sí |  |  |  |
| monto_descuento | DOUBLE | Sí |  |  |  |
| vigencia_desde | DATE | Sí |  |  |  |
| vigencia_hasta | DATE | Sí |  |  |  |
| lista1 | VARCHAR | Sí |  |  |  |
| lista2 | VARCHAR | Sí |  |  |  |
| lista3 | VARCHAR | Sí |  |  |  |
| lista4 | VARCHAR | Sí |  |  |  |
| lista5 | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |

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
| Articulo_Promo_Carga.frm | 707 | SELECT | rs_promo.Open "SELECT * FROM articulo_promo_intervalo WHERE … |
| Articulo_Promo_Carga.frm | 746 | SELECT | rs_promo.Open "SELECT * FROM articulo_promo_intervalo WHERE … |
| Articulo_Promo_ABM.frm | 438 | SELECT | rs_promo.Open "SELECT * FROM articulo_promo_intervalo WHERE … |
| Articulo_Promo_ABM.frm | 441 | SELECT | conn.Execute "delete from articulo_promo_intervalo where id_… |
| Articulo_Promo_ABM.frm | 441 | DELETE | conn.Execute "delete from articulo_promo_intervalo where id_… |
| Articulo_Promo_ABM.frm | 600 | SELECT | '    data_promo_intervalo.RecordSource = "SELECT * FROM arti… |
| Articulo_Promo_ABM.frm | 614 | JOIN | " LEFT JOIN articulo_promo_intervalo ON (articulo_promo_inte… |
| Principal.frm | 13283 | SELECT | rs_consulta_promo.Open "SELECT * FROM articulo_promo_interva… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)