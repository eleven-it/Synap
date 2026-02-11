# Tabla `ecom_info_articulo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ecom_info_articulo | BIGINT | No | ✓ |  |  |
| id_articulo | BIGINT | Sí |  |  |  |
| destacado_ecom | VARCHAR | Sí |  |  |  |
| promo_solo_web | VARCHAR | Sí |  |  |  |
| descuento_solo_web | DOUBLE | Sí |  |  |  |
| vigencia_desde_solo_web | DATE | Sí |  |  |  |
| vigencia_hasta_solo_web | DATE | Sí |  |  |  |
| detalle_descuento_especial | MEDIUMTEXT | Sí |  |  |  |
| detalle_ecom | LONGTEXT | Sí |  |  |  |
| caracteristicas_ecom | LONGTEXT | Sí |  |  |  |
| nombre_articulo_ecom | VARCHAR | Sí |  |  |  |
| usa_nombre_articulo_ecom | VARCHAR | Sí |  |  |  |
| link_articulo_ecom | VARCHAR | Sí |  |  |  |
| link_video_articulo_ecom | VARCHAR | Sí |  |  |  |
| link_archivo_articulo_ecom | VARCHAR | Sí |  |  |  |
| dimension_articulo | VARCHAR | Sí |  |  |  |
| dimension_articulo_ancho | INT | Sí |  |  |  |
| dimension_articulo_alto | INT | Sí |  |  |  |
| dimension_articulo_largo | INT | Sí |  |  |  |
| dimension_articulo_peso | DECIMAL | Sí |  |  |  |
| garantia_articulo | INT | Sí |  |  |  |
| financiacion_articulo | VARCHAR | Sí |  |  |  |
| cuotas_articulo | INT | Sí |  |  |  |
| recargo_financiacion | DECIMAL | Sí |  |  |  |
| cft_financiacion | DECIMAL | Sí |  |  |  |
| tna_financiacion | INT | Sí |  |  |  |
| vigencia_desde_financiacion | DATE | Sí |  |  |  |
| vigencia_hasta_financiacion | DATE | Sí |  |  |  |
| id_ecom_caract_plantilla | BIGINT | Sí |  |  |  |
| ecom_externo | VARCHAR | Sí |  |  |  |
| peso_articulo | DECIMAL | Sí |  |  |  |
| tipo_envio | VARCHAR | Sí |  |  |  |
| id_ecom_externo | BIGINT | Sí |  |  |  |
| sku_ecom_externo | VARCHAR | Sí |  |  |  |
| slug_ecom_externo | VARCHAR | Sí |  |  |  |
| categorias_ecom_externo | VARCHAR | Sí |  |  |  |
| publicado_ecom_externo | VARCHAR | Sí |  |  |  |
| tags_ecom_externo | VARCHAR | Sí |  |  |  |
| imagen_ecom_externo | MEDIUMTEXT | Sí |  |  |  |
| imagen_galeria_ecom_externo | MEDIUMTEXT | Sí |  |  |  |
| link_articulo_qr_ecom | VARCHAR | Sí |  |  |  |

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
| Exportacion.frm | 7667 | JOIN | " LEFT JOIN ecom_info_articulo ON (ecom_info_articulo.id_art… |
| ecom_datos_articulo.frm | 2654 | SELECT | rs_alta_mod.Open "SELECT * FROM ecom_info_articulo WHERE id_… |
| ecom_datos_articulo.frm | 2664 | SELECT | rs_alta_mod.Open "SELECT * FROM ecom_info_articulo WHERE id_… |
| ecom_datos_articulo.frm | 3211 | JOIN | " LEFT JOIN ecom_info_articulo ON (ecom_info_articulo.id_art… |
| Funciones.bas | 9338 | SELECT | '        rs_consulta.Open "SELECT id_articulo,id_ecom_info_a… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)