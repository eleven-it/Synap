# Tabla `nro_codigo_manual_cliente`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id | BIGINT | No | ✓ |  |  |
| nro_cod_manual_cliente | BIGINT | Sí |  |  |  |

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
| Configuracion_Adicional2.frm | 3965 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| Configuracion_Adicional2.frm | 4091 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| Configuracion2.frm | 4597 | SELECT | '        rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_… |
| Configuracion2.frm | 5209 | SELECT | '    rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codi… |
| Configuracion.frm | 4690 | SELECT | '        rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_… |
| Configuracion.frm | 5308 | SELECT | '    rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codi… |
| VariacionPrecio.frm | 7042 | SELECT | '            rs_nro_auto_cod_manual_art.Open "SELECT * FROM … |
| VariacionPrecio.frm | 7056 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| Configuracion_Adicional.frm | 4161 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| Configuracion_Adicional.frm | 4298 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| CargaArticulo.frm | 10672 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| Configuracion.frm | 5045 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| Configuracion.frm | 5656 | SELECT | rs_nro_auto_cod_manual_art.Open "SELECT * FROM nro_codigo_ma… |
| Funciones.bas | 4983 | SELECT | rs_consulta.Open "SELECT * FROM nro_codigo_manual_cliente WH… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)