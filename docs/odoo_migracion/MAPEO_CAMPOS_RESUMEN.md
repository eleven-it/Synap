# Mapeo de campos — resumen por dominio

External ID canónico: `ref = adminet/<entidad>/<pk>`.

## Empresa (`datosempresa` → `res.company`)

| AdministraNET | Odoo | Notas |
|---------------|------|-------|
| id_empresa | ref | PK |
| Nombre | name | |
| CUIT | vat | sin guiones |
| Domicilio | street | |
| Telefono | phone | |
| Email | email | |

## Rubro / subrubro (`rubro`, `subrubro` → `product.category`)

| AdministraNET | Odoo |
|---------------|------|
| CodigoRubro / IDSubRubro | ref |
| NombreRubro / NombreSubRubro | name |
| CodigoRubro (subrubro) | parent_id vía mapping rubro |

## Marca (`marca` → `adm.product.brand`)

| AdministraNET | Odoo |
|---------------|------|
| CodMarca | code, ref |
| NombreMarca | name |
| anulado | active |

## Vendedor (`viajantes` → `res.partner`)

| AdministraNET | Odoo |
|---------------|------|
| CodViajante | ref |
| Nombre | name |

## Cliente / proveedor (`cliente`, `proveedor` → `res.partner`)

| AdministraNET | Odoo |
|---------------|------|
| Codigo | ref |
| nombre_cliente / Nombre | name |
| CUIT | vat |
| Calle | street |
| Email | email |
| — | customer_rank / supplier_rank |

## Artículo (`articulo` → `product.template`)

| AdministraNET | Odoo |
|---------------|------|
| IDArt | ref |
| NombreArticulo | name |
| CodigoArticulo | default_code |
| Precio1V | list_price |
| PrecioCosto | standard_price |
| CodigoMarca | adm_brand_id (mapping) |
| id_unimed | uom_id (mapping) |
| CodigoRubro / IDSubRubro | categ_id (mapping) |

## Stock (`stock_deposito` → `stock.quant`)

| AdministraNET | Odoo |
|---------------|------|
| id_stock_deposito | ref |
| id_articulo + id_deposito | product + location (vía mappings) |
| saldo | quantity (wizard ajuste) |

## Factura CC (`cuentacliente` → `account.move`)

| AdministraNET | Odoo |
|---------------|------|
| id_cuentacliente | ref |
| TipoComprobante | move_type |
| saldo | amount_residual (histórico) |
| Fecha | invoice_date |

**Sin re-emisión CAE.** Estado mapping: `PENDIENTE` hasta importación manual supervisada.

## Código

Mappers en `odoo_migracion/mappers/__init__.py`.
