# Reglas de convivencia AdministraNET ↔ Odoo

## Principios

1. **Maestros:** AdministraNET es maestro hasta cutover → sync unidireccional `adminet_to_odoo`.
2. **Stock:** un solo sistema mueve inventario; Synap registra snapshots y mappings `PENDIENTE` para ajuste vía wizard Odoo.
3. **Facturas AFIP:** no re-emitir CAE; solo histórico + saldos en Odoo (`pending_manual`).
4. **Idempotencia:** `MigrationEntityMapping` + `ref` estable `adminet/<entidad>/<id>`.

## Por dominio

| Dominio | Sistema maestro | Dirección sync |
|---------|-----------------|----------------|
| empresa | AdministraNET | adminet_to_odoo |
| cliente / proveedor | AdministraNET | adminet_to_odoo |
| articulo | AdministraNET | adminet_to_odoo |
| stock_saldo | AdministraNET (snapshot) | snapshot |
| cuenta_cliente | AdministraNET (histórico) | manual |

## Código

Reglas en `odoo_migracion/services/coexistence.py` (`COEXISTENCE_RULES`).

## Cutover

1. Congelar talonarios AdministraNET para tipos que pasen a Odoo.
2. Cuadre final (`odoo_validate_migration`).
3. Activar emisión solo en Odoo.
