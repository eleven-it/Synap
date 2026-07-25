# Tabla `sucursales_envios`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sucursales_envios | BIGINT | No | ✓ |  |  |
| id_sucusal | BIGINT | Sí |  |  |  |
| tipo_envio | VARCHAR | Sí |  |  |  |
| id_zona | BIGINT | Sí |  |  |  |
| porcentaje_descuento | DOUBLE | Sí |  |  |  |
| tipo_recargo_envio | VARCHAR | Sí |  |  |  |
| tipo_recargo_envio_monto | DOUBLE | Sí |  |  |  |
| monto_minimo_envio_gratis | DECIMAL | Sí |  |  |  |
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
| ABM_Sucursal_Envio.frm | 438 | SELECT | Data_Tipo_Envio.RecordSource = "SELECT sucursales_envios.*,e… |
| ABM_Sucursal_Envio.frm | 541 | SELECT | conn.Execute "delete from sucursales_envios where id_sucursa… |
| ABM_Sucursal_Envio.frm | 541 | DELETE | conn.Execute "delete from sucursales_envios where id_sucursa… |
| CargaSucursal_Envio.frm | 572 | SELECT | rs.Open "SELECT * FROM sucursales_envios WHERE id_sucursales… |
| CargaSucursal_Envio.frm | 603 | SELECT | rs.Open "SELECT * FROM sucursales_envios WHERE id_sucursales… |
| Funciones.bas | 14623 | JOIN | " LEFT JOIN sucursales_envios ON (sucursales_envios.id_sucur… |
| Funciones.bas | 15048 | JOIN | " LEFT JOIN sucursales_envios ON (sucursales_envios.id_sucur… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)