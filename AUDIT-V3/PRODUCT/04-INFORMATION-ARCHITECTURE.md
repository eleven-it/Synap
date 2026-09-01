# 04 — Information Architecture

**Estado:** COMPLETE

## Jerarquía actual

```text
Navbar APPS_MENU (18 apps)
  → App sidebar (secciones filtradas por permiso)
    → Screen (template + URL)
      → Actions (botones, tabs, modales)
```

**Source:** `core/utils/utils.py` APPS_MENU, `core/context_processors.py` menu_context.

## Profundidad típica

| App | Niveles menú → pantalla | Max depth |
|-----|------------------------|:---------:|
| MPR | 3 (Producción → Armado → pantalla) | 4 |
| Ecom | 3 (Portal → Pedidos → hub) | 3 |
| Reports | 2 (Catálogo → dashboard) | 2 |
| Core/Archivo | 3 (Parámetros → Usuarios → editar) | 4 |

## Duplicaciones detectadas

| Concepto | Rutas duplicadas |
|----------|------------------|
| Pedidos | Ventas menú + Ecom menú → mismo hub |
| Pedido masivo | Ventas + Ecom |
| Inventario depósito | Reports + MPR reportes |
| Settings vs Archivo | overlap usuarios/empresa |

## Inconsistencias

- Menú inglés (Settings, Reports) vs español (Producción, Stock)
- `ventas/objetivos-venta` excluido como referencia UI pero activo en menú
- Sidebar modelado pero muchas pantallas usan `no-sidebar` (`base_app.html`)

## Rutas huérfanas / legacy

- `/dashboard/` stub (`dashboard/templates/`)
- Templates `* 2.html` (self_checkout, reports, compras) — posible drift

## Nombres distintos, mismo concepto

| Concepto | Variantes UI |
|----------|--------------|
| Informe / Report / Dashboard | reports catalog vs dashboard slug |
| Pedido / Orden / comp_ped | ecom vs ventas labels |
| Kiosco / TPV / Self-checkout | menú vs URLs |
