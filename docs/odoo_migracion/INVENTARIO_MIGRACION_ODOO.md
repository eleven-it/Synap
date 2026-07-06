# Inventario de migración (F0)

Metodología alineada a [`INVENTARIO_MIGRACION_FORMULARIOS.md`](../general/INVENTARIO_MIGRACION_FORMULARIOS.md).

## Comando

```bash
docker exec Synap_app python manage.py odoo_discovery --base-empresa=NOMBRE_BASE
docker exec Synap_app python manage.py odoo_discovery --base-empresa=NOMBRE_BASE --json
```

## UI

`/odoo-migracion/inventario/` — solo usuario `supervisor`.

## Conteos por dominio

| Dominio | Tabla principal | Filtro habitual |
|---------|-----------------|-----------------|
| empresa | datosempresa | — |
| rubro | rubro | anulado = No |
| cliente | cliente | Estado = Activo |
| articulo | articulo | Discontinuo = No |
| stock_saldo | stock_deposito | saldo <> 0 |
| cuenta_cliente | cuentacliente | saldo > 0, no anulado |

## Anomalías automáticas

- Clientes activos sin CUIT
- Artículos sin rubro o UoM
- Saldos negativos
- Facturas abiertas con saldo cero

Ejecutar **antes** del wizard de migración en cada `base_empresa` piloto.
