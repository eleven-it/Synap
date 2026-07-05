# Inventario hub mayoristapp (F0)

**PHP:** `administraNET-ecom/mayoristapp/componente-menu-card-dashboard.php`  
**Synap:** `GET /ecom/mayoristapp/` — `HubMayoristappView` + `ecom/templates/ecom/hub_mayoristapp.html`

## Cards (1:1)

| Card PHP | Card Synap | Enlaces activos F0 | Pendiente |
|----------|------------|-------------------|-----------|
| Ventas | Ventas | Compra, PDF lista precios | Promociones, Pedidos (F1) |
| Logística | Logística | Preparación pedidos, Comprobantes en ruta (reports) | Devoluciones (F1) |
| Clientes | Clientes | — | F1/F2 |
| Stock | Stock | — | F1/F3 inventario SPA |
| Comprobantes emitidos | Comprobantes emitidos | Presupuestos vendedor | FE, recibos, NC, remitos (F1) |
| Estadísticas | Estadísticas | 3 dashboards reports | Dashboard agregado PHP |
| Premios | Premios | — | F3 |

## Componentes UI

| PHP | Synap |
|-----|--------|
| Grid `.cards-grid` | Grid Tailwind `md:grid-cols-2 xl:grid-cols-3` |
| Icono Font Awesome | `material-symbols-outlined` |
| Enlaces `<a href>` | `reverse(url_name)` o placeholder “Próximamente” |

## Gaps aceptados F0

- Entradas deshabilitadas muestran nota de fase (F1/F2/F3).
- Premios condicional PHP (`modulo_premios` sesión) → siempre visible deshabilitado hasta F3.
