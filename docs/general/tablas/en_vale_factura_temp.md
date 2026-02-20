# Tabla `en_vale_factura_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_vale_factura_temp | BIGINT | No | ✓ |  |  |
| id_vale | BIGINT | Sí |  |  |  |
| codmov_vale | BIGINT | Sí |  |  |  |
| codigo_proveedor | BIGINT | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| importe_neto | DECIMAL | Sí |  |  |  |
| nombre_materia_prima | VARCHAR | Sí |  |  |  |

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
| PFactura.frm | 3892 | SELECT | rs_hay_vale.Open " SELECT * FROM en_vale_factura_temp WHERE … |
| PFactura.frm | 4170 | SELECT | conn.Execute "INSERT INTO en_vale_factura(CodMovVale,CodMovF… |
| PFactura.frm | 4178 | SELECT | .Source = "SELECT * FROM en_vale_factura_temp WHERE en_vale_… |
| En_Liquidacion_Vales.frm | 2275 | SELECT | consulta = " SELECT * FROM en_vale_factura_temp WHERE id_en_… |
| En_Liquidacion_Vales.frm | 2299 | SELECT | consulta = " SELECT * FROM en_vale_factura_temp WHERE id_usu… |
| En_Liquidacion_Vales.frm | 2333 | SELECT | rs_vales_tmp.Open "SELECT * FROM en_vale_factura_temp WHERE … |
| En_Liquidacion_Vales.frm | 2666 | SELECT | conn.Execute "DELETE FROM en_vale_factura_temp WHERE id_usua… |
| En_Liquidacion_Vales.frm | 2666 | DELETE | conn.Execute "DELETE FROM en_vale_factura_temp WHERE id_usua… |
| Principal.frm | 6116 | SELECT | conn.Execute "delete from en_vale_factura_temp where id_usua… |
| Principal.frm | 6116 | DELETE | conn.Execute "delete from en_vale_factura_temp where id_usua… |
| Principal.frm | 6182 | SELECT | conn.Execute "delete from en_vale_factura_temp where id_usua… |
| Principal.frm | 6182 | DELETE | conn.Execute "delete from en_vale_factura_temp where id_usua… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)