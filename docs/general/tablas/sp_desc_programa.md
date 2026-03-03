# Tabla `sp_desc_programa`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sp_desc | BIGINT | No | ✓ |  |  |
| nombre_sp_desc | VARCHAR | Sí |  |  |  |
| tipo_sp_desc | VARCHAR | Sí |  |  |  |
| monto_descuento | DOUBLE | Sí |  |  |  |
| puntos_consumido | DOUBLE | Sí |  |  |  |
| id_articulo | BIGINT | Sí |  |  |  |
| id_rubro | BIGINT | Sí |  |  |  |
| id_subrubro | BIGINT | Sí |  |  |  |
| id_marca | BIGINT | Sí |  |  |  |
| id_proveedor | BIGINT | Sí |  |  |  |
| Id_categoria | BIGINT | Sí |  |  |  |
| vencimiento | DATE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_programa | VARCHAR | Sí |  |  |  |
| codigo_barra_voucher | VARCHAR | Sí |  |  |  |
| imprime_voucher | VARCHAR | Sí |  |  |  |
| envia_mail | VARCHAR | Sí |  |  |  |
| desde | DATE | Sí |  |  |  |
| hasta | DATE | Sí |  |  |  |
| limite_compra | DOUBLE | Sí |  |  |  |
| imagen | LONGBLOB | Sí |  |  |  |
| texto_adicional | MEDIUMTEXT | Sí |  |  |  |
| nro_actual_cupon | BIGINT | Sí |  |  |  |
| ruta_reporte | VARCHAR | Sí |  |  |  |
| tipo_voucher | VARCHAR | Sí |  |  |  |
| tope_reintegro_voucher | DOUBLE | Sí |  |  |  |
| proceso | VARCHAR | Sí |  |  |  |

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
| TPV.frm | 40353 | SELECT | rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon,tipo_pr… |
| TPV.frm | 40369 | SELECT | rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon,tipo_pr… |
| FacturaB.frm | 27460 | SELECT | '    rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon FR… |
| FacturaB.frm | 27539 | SELECT | rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon,tipo_pr… |
| FacturaB.frm | 27555 | SELECT | rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon,tipo_pr… |
| Programa_Descuentos.frm | 2372 | SELECT | "FROM sp_desc_programa " & _ |
| FacturaA.frm | 23278 | SELECT | '    rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon FR… |
| FacturaA.frm | 23357 | SELECT | rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon,tipo_pr… |
| FacturaA.frm | 23373 | SELECT | rs_consulta.Open "SELECT id_sp_desc,nro_actual_cupon,tipo_pr… |
| Programa_Descuentos_Carga.frm | 2407 | SELECT | rs_programa_descuento.Open "SELECT * FROM sp_desc_programa W… |
| Programa_Descuentos_Carga.frm | 2423 | SELECT | rs_programa_descuento.Open "SELECT * FROM sp_desc_programa W… |
| Programa_Descuentos_Carga.frm | 2537 | SELECT | rs_programa_descuento.Open "SELECT * FROM sp_desc_programa W… |
| Programa_Descuentos_Carga.frm | 3180 | SELECT | rs.Open "SELECT * FROM sp_desc_programa WHERE id_sp_desc = "… |
| Programa_Descuentos_Canje.frm | 966 | SELECT | "FROM sp_desc_programa " & _ |
| Visualiza.bas | 21953 | SELECT | rs_consulta.Open "SELECT * FROM sp_desc_programa WHERE  " & … |
| Funciones.bas | 11551 | JOIN | " LEFT JOIN sp_desc_programa ON (sp_desc_programa.id_sp_desc… |
| Funciones.bas | 12286 | SELECT | rs_consulta.Open "SELECT nombre_sp_desc,id_sp_desc,puntos_co… |
| Funciones.bas | 15443 | SELECT | " FROM sp_desc_programa " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)