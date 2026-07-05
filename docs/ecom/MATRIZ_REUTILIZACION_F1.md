# Matriz de reutilización F1 — mayoristapp

**Fecha:** 04/07/2026  
**Alcance:** Fase 1 núcleo vendedor web (post F0 fundaciones).  
**Metodología:** Por cada vertical PHP → ¿existe en Synap? → reutilizar / extender / enlazar reports / duplicar / diferir F2–F3.

---

## Resumen ejecutivo

| Patrón | Verticals |
|--------|-----------|
| **Backend OK, falta UI shell** | Promociones, clientes, FE, recibos, NC, remitos, devoluciones |
| **Enlazar reports (no duplicar)** | Stock existencias, estadísticas, comprobantes-rutas |
| **Reutilizar ecom existente** | Pedidos (API), presupuestos portal, compra/checkout, kanban preparación, entregas |
| **Nueva implementación** | Pedidos detalle/export, artículos remito, alta recibo, pallet checkout |
| **F2/F3** | Portal cliente ABM, premios, inventario SPA, tmobile |

---

## Matriz por vertical

| Vertical | PHP principal | Synap actual | Acción F1 | Notas |
|----------|---------------|--------------|-----------|-------|
| **Hub navegación** | `componente-menu-card-dashboard.php` | `HubMayoristappView` | **Reutilizar** | Cards F1 se activan al migrar cada pantalla |
| **Compra / checkout PED** | `alta_pedido.php`, `jcart/` | `compra_mayorista.html` + checkout API | **Reutilizar** | Gaps: pallet, promos línea → F1-api-gaps |
| **Pedidos listado vendedor** | `lista-pedidos-vendedor.php`, `relay-pedidos.php` | API v1 + UI ✅ | **Extender** | Detalle v1 ✅; export PDF pendiente |
| **Remitos / FE / NC / Recibos / Devoluciones** | `lista_*.php` | APIs + UI genérica ✅ | **Extender** | Shell `listado_mayoristapp` |
| **Promociones** | `lista-promociones.php` | API + UI ✅ | **Extender** | |
| **Clientes listado** | `listado-clientes.php` | API + UI búsqueda ✅ | **Extender** | ABM F2 |
| **Artículos remitados** | `relay-articulo-remito.php` | API + UI ✅ | **Duplicar** | Servicio nuevo |
| **Portal cliente F2** | ctacte/consumos/nc | APIs + UI portal ✅ | **Extender** | Requiere idcliente sesión |
| **Estado preparación** | `logistica_pantalla_preparacion.php` | `estado_pedidos_preparacion` ✅ | **Reutilizar** | Operativo depósito |
| **Comprobantes en ruta** | `logistica_lista_comprobantes_rutas.php` | reports `comprobantes-rutas` + logistica | **Enlazar** | Hub ya enlazado |
| **Entregas en ruta** | PHP logística | `logistica/entregas/` | **Enlazar** | ecom 301 → logistica |
| **Stock existencias** | `listado-stock-existencias.php` | reports `stock-existencias` ✅ | **Enlazar** | Activar hub → reports |
| **Artículos remitados** | `lista-articulo-remito.php` | Sin migrar | **Duplicar** | Nuevo servicio + UI F1 |
| **Estadísticas / informes** | `dashboard-estadisticas.php` | reports dashboards | **Enlazar** | No duplicar runners en ecom |
| **Ventas netas** | relay PHP | reports relay parcial | **Extender reports** | No ecom |
| **Objetivos venta** | JSON PHP | ventas + reports BO | **Enlazar** | No portar PHP |
| **Presupuesto ERP** | VB6 / ventas | `ventas/presupuestos/` | **Paralelo** | Distinto del portal carrito |
| **Alta recibo** | `alta_recibo*.php` | Sin escritura | **Nueva impl.** | F1/F2 cobranzas |
| **Premios** | `modulo_premios` | No existe | **F3** | Decisión producto |
| **Inventario SPA** | `inventario/index.php` | No existe | **F3** | Scanner + imágenes |
| **tmobile jcart** | móvil PHP | No existe | **F3** | |

---

## Módulos Synap — rol en F1

| Módulo | Rol | Regla |
|--------|-----|-------|
| **ecom/** | Portal vendedor: UI listados, APIs comprobantes, carrito | Canónico para operación mayoristapp |
| **reports/** | Informes agregados, stock existencias, rutas, KPIs | Enlazar desde hub; no duplicar SQL |
| **logistica/** | Entregas, remitos en ruta | Reutilizar; ecom solo enlaza |
| **ventas/** | Presupuestos ERP backoffice | No mezclar con portal ecom |
| **self_checkout/** | `StockService` | Reutilizar para existencias si reports no alcanza |
| **fe_afip/** | Emisión CAE TPV | Escritura FE cruzar con fe_afip, no solo ecom |

---

## Secuencia F1 acordada

1. ✅ Matriz documentada (este archivo).
2. 🔄 **Piloto pedidos** — UI vendedor + consumo API v1 (`/ecom/mayoristapp/pedidos-vendedor/`).
3. Enlaces hub → reports (stock existencias).
4. Shells ecom: promociones, clientes, FE, recibos, NC, remitos, devoluciones.
5. API gaps: detalle pedido, export, `campoAnulado`, artículo-remito, pallet.

---

## Referencias

- Plan maestro: `.cursor/plans/migración_ecom_100%_a0980ea0.plan.md`
- Inventario pedidos: `docs/ecom/INVENTARIO_FORMULARIO_PEDIDOS_MAYORISTAPP.md`
- API v1: `docs/ecom/API_REST_V1_MAPPING.md`
- Relays: `docs/ecom/MAYORISTAPP_RELAYS.md`
