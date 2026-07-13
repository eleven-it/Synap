# Exploration — Pedidos hub kanban + carga masiva sucursales

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales`  
**Fecha:** 13/07/2026

## Contexto actual

| Pieza | Estado |
|-------|--------|
| `/ecom/mayoristapp/pedidos/` | Hub KPI + CTAs (`pedidos_hub.html`) — a reemplazar como home |
| `/ecom/mayoristapp/compra/` | OrderShell PED simple + `EcomCart` borrador |
| Listado vendedor / kanban depósito | Existen; kanban prep = solo lectura logística |
| `cliente_domicilio` + `cliente_datos_adicionales` | Checkout ya graba `id_cliente_domicilio` |
| Marcas en catálogo | Filtro opcional UI, no territorio comercial |
| Usuario ↔ viajante | Sesión `cod_viajante`; sin ABM tipo MPR operario |
| Canon UI | Tablero producción MPR (slate-800, matriz sticky) |

## Problema

1. Home de pedidos no es operativa (no muestra borradores ni pipeline).
2. No hay exclusividad comercial Vendedor→Cliente→Marca.
3. No hay carga multi-sucursal (N PED) con matriz packs.
4. Fallos de confirmación / cierre accidental no pueden perder la carga.

## Enfoques evaluados

| Opción | Pros | Contras | Decisión |
|--------|------|---------|----------|
| A. Extender OrderShell a multi-domicilio | Reusa UI | No escala a N columnas; confunde 1 PED | Rechazada |
| B. Hub Lista+Kanban + matriz dedicada + config | Claro, Odoo-like, canon tablero | Más pantallas | **Elegida** |
| C. Un solo PED multi-domicilio en Admin | Menos comprobantes | Rompe modelo Admin/rutas | Rechazada |

## Dependencias

- Specs: `ecom-checkout-mayorista`, `ecom-carrito-mayorista`, `ecom-catalogo-producto-mayorista`
- Patrón mapeo: `mpr_operario_usuario` / `services_operario`
- Schema MySQL: catálogo `legacy_mysql_schema` + DDL en `ecom/sql/`
