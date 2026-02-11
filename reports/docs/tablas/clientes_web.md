# Tabla `clientes_web`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_usuario_web | INT | No | ✓ |  |  |
| codigo_usuario | VARCHAR | No |  |  |  |
| clave_usuario | BLOB | No |  |  |  |
| Codigo | INT | No |  |  |  |
| tipo_cliente | VARCHAR | No |  |  |  |
| activo_usuario | VARCHAR | No |  |  |  |
| clave_usuario_temporal | VARCHAR | Sí |  |  |  |
| tipo_cuenta | VARCHAR | Sí |  |  |  |
| oath_proveedor | VARCHAR | Sí |  |  |  |
| nombre_usuario | VARCHAR | Sí |  |  |  |
| token | VARCHAR | Sí |  |  |  |
| avatar | VARCHAR | Sí |  |  |  |
| sexo | VARCHAR | Sí |  |  |  |
| ultima_session | VARCHAR | Sí |  |  |  |

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
| Cliente.frm | 3548 | SELECT | rs_clientes_web.Open "SELECT * FROM clientes_web WHERE Codig… |
| Cliente.frm | 3551 | UPDATE | conn.Execute "UPDATE clientes_web SET clave_usuario_temporal… |
| Cliente.frm | 3558 | SELECT | .Source = "SELECT clave_usuario_temporal as clave FROM clien… |
| Cliente.frm | 3566 | UPDATE | conn.Execute "UPDATE clientes_web SET clave_usuario_temporal… |
| Facturacion.frm | 3765 | SELECT | rs_clientes_web.Open "SELECT * FROM clientes_web WHERE Codig… |
| Facturacion.frm | 3768 | UPDATE | conn.Execute "UPDATE clientes_web SET clave_usuario_temporal… |
| Facturacion.frm | 3775 | SELECT | .Source = "SELECT clave_usuario_temporal as clave FROM clien… |
| Facturacion.frm | 3783 | UPDATE | conn.Execute "UPDATE clientes_web SET clave_usuario_temporal… |
| Carga_Cliente.frm | 5531 | SELECT | rs_ecommerce.Open "SELECT * FROM clientes_web WHERE id_usuar… |
| Carga_Cliente.frm | 5539 | UPDATE | conn.Execute "UPDATE clientes_web SET clave_usuario=AES_ENCR… |
| Carga_Cliente.frm | 5903 | SELECT | rs_ecommerce.Open "SELECT * FROM clientes_web WHERE Codigo =… |
| Carga_Cliente.frm | 5919 | UPDATE | conn.Execute "UPDATE clientes_web SET clave_usuario=AES_ENCR… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)