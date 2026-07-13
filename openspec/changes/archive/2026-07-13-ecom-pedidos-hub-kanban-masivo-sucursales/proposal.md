# Proposal: Pedidos hub Lista/Kanban + masivo por sucursales

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales`  
**Fecha:** 13/07/2026

## Intent

Refactorizar `/ecom/mayoristapp/pedidos/` como home operativa (Lista + Kanban estilo Odoo, canon Tablero producción). Desde ahí: recuperar borradores, ver PED enviados/aprobados, crear pedido simple o **masivo por sucursales** (matriz artículo×sucursal → 1 PED por domicilio). Configurar territorio **Vendedor→Cliente→Marca** sin solape de marca por cliente. Borrador persistente ante rollback o cierre accidental.

## Scope

### In Scope
- Refactor hub → Lista | Kanban (borrador, enviado, por autorizar, aprobado, anulado)
- ABM config Vendedor→Cliente→Marca + permisos supervisor
- Pantalla matriz masiva + borrador Postgres + batch checkout con rollback → borrador
- Filtro catálogo por marcas asignadas al par vendedor-cliente
- Docs `docs/ecom/`, tests, menú/permisos Synap

### Out of Scope
- Drag-and-drop para cambiar estado de PED Admin (salvo autorizar)
- Unificar PED multi-domicilio en un solo comprobante Admin
- Rediseño completo del OrderShell simple (solo enlaces desde hub)
- App móvil nativa de la matriz

## Capabilities

### New Capabilities
- `ecom-pedidos-hub-kanban`: home Lista/Kanban; recuperacion borradores; CTA Nuevo
- `ecom-vendedor-cliente-marca`: ternas + unique (cliente, marca); mapeo usuario↔viajante si falta
- `ecom-pedido-masivo-sucursales`: matriz, borrador, batch PED por `cliente_domicilio`

### Modified Capabilities
- `ecom-catalogo-producto-mayorista`: filtro obligatorio marcas de terna en flujo masivo
- `ecom-checkout-mayorista`: API/lote multi-PED con rollback; `id_cliente_domicilio` por PED

## Approach

Postgres: borrador matriz + ternas (o MySQL snake_case vía catálogo legacy según diseño). Reutilizar `mayorista_checkout_service` por sucursal en transacción lógica de lote. UI: shell tipo `tablero_produccion.html`.

## Affected Areas

| Area | Impact |
|------|--------|
| `ecom/templates/ecom/pedidos_hub.html` | Reemplazo / refactor fuerte |
| `ecom/mayoristapp_web_views.py`, `urls.py` | Rutas hub, config, masivo |
| `ecom/models.py` / SQL schema | Borrador masivo, ternas |
| `ecom/services/*` | Pipeline hub, batch, catálogo filtrado |
| `core/.../administranet_permisos*` / seed | Permisos nuevos |
| `docs/ecom/` | Documentación operativa |

## Risks

| Risk | L | Mitigation |
|------|---|------------|
| Batch parcial deja PED huérfanos | Med | Rollback Admin + borrador intacto + errores por sucursal |
| Solape marcas en datos legacy | Med | Unique + UI conflicto + migración dry-run |
| Hub lento con muchos PED | Med | Paginación, scope por viajante, índices |

## Rollback Plan

Feature flags / permisos off; restaurar template hub KPI; no borrar tablas (soft). Revert commit change.

## Dependencies

- Checkout mayorista P2 estable; `cliente_domicilio` poblado
- Sesión `cod_viajante` o mapeo explícito

## Success Criteria

- [ ] `/pedidos/` es Lista|Kanban y muestra borradores recuperables
- [ ] Config bloquea marca duplicada (cliente, marca)
- [ ] Masivo crea N PED o 0; borrador no se pierde
- [ ] Canon visual alineado a tablero producción
- [ ] Tests + docs en español
