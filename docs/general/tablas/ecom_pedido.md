# Tabla `ecom_pedido`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ecom_pedido | BIGINT | No | ✓ |  |  |
| tipo_ecom_pedido | VARCHAR | Sí |  |  |  |
| estado_ecom_pedido | VARCHAR | Sí |  |  |  |
| codigo_movimiento_ped | BIGINT | Sí |  |  |  |
| json_devuelto | MEDIUMTEXT | Sí |  |  |  |
| entidad_pago | VARCHAR | Sí |  |  |  |
| forma_pago_mp | VARCHAR | Sí |  |  |  |
| porcentaje_comision_mp | DOUBLE | Sí |  |  |  |
| importe_comision_mp | DOUBLE | Sí |  |  |  |
| importe_financiacion_mp | DOUBLE | Sí |  |  |  |
| importe_total_comision_mp | DOUBLE | Sí |  |  |  |
| importe_total_pago_mp | DOUBLE | Sí |  |  |  |
| importe_saldo_mp | DOUBLE | Sí |  |  |  |
| forma_cobro_ml | VARCHAR | Sí |  |  |  |
| metodo_cobro_ml | VARCHAR | Sí |  |  |  |
| tarjeta_cobro_mp | VARCHAR | Sí |  |  |  |
| cuotas_mp | INT | Sí |  |  |  |
| importe_cuotas_mp | DOUBLE | Sí |  |  |  |
| tipo_envio | VARCHAR | Sí |  |  |  |
| empresa_envio_ecom | VARCHAR | Sí |  |  |  |
| id_transporte | BIGINT | Sí |  |  |  |
| forma_envio_ml | VARCHAR | Sí |  |  |  |
| domicilio_texto_ml | VARCHAR | Sí |  |  |  |
| id_cliente_domicilio | DOUBLE | Sí |  |  |  |
| importe_envio | DOUBLE | Sí |  |  |  |
| nro_transaccion_mp | VARCHAR | Sí |  |  |  |
| nro_transaccion_ml | VARCHAR | Sí |  |  |  |
| datos_tarjeta_cobro | MEDIUMTEXT | Sí |  |  |  |
| importe_tarjeta_mp | DOUBLE | Sí |  |  |  |
| nro_transaccion_envio | VARCHAR | Sí |  |  |  |
| json_envio | MEDIUMTEXT | Sí |  |  |  |
| xml_envio | TEXT | Sí |  |  |  |
| link_externo_etiqueta | VARCHAR | Sí |  |  |  |
| id_cliente_web | INT | Sí |  |  |  |
| nro_transaccion_ecom_externo | VARCHAR | Sí |  |  |  |

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
| ecom_datos_pedido.frm | 883 | SELECT | " FROM ecom_pedido " & _ |
| Funciones.bas | 14652 | SELECT | " FROM ecom_pedido " & _ |
| Funciones.bas | 15077 | SELECT | " FROM ecom_pedido " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)