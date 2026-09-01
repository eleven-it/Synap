# 03 — Mapa de Navegación

**Estado:** COMPLETE

## Global

```text
Navbar (theme/partials/navbar.html)
  ├── Dropdown APPS_MENU (18 apps, filtrado permisos)
  ├── Status bar (empresa, sucursal, fecha servidor)
  └── User menu (perfil, logout)
```

**Source:** `core/context_processors.py:menu_context`, `core/utils/utils.py:APPS_MENU`.

## Por app (sidebar cuando aplica)

| App | Secciones sidebar | URL prefix |
|-----|-------------------|------------|
| Archivo | Parámetros (empresa, usuarios, permisos…) | `/core/` |
| Stock | Movimientos, Consultas, Comprobantes | `/stock/` |
| Ventas | Comprobantes, Gestión, Objetivos | `/ventas/` + `/ecom/` |
| MPR | Producción, Armado, Reportes, Config | `/mpr/` |
| Ecom | Portal, Comprobantes, Clientes, Logística | `/ecom/` |
| Reports | Catálogo, Workspace | `/reports/` |
| TPV | Kioscos, Config, Talonarios | `/self_checkout/` |

## MPR quick-nav

`{% block mpr_quick_nav %}` en `base_mpr.html` — navegación contextual superior en producción.

## Breadcrumbs

- **Ausentes** en mayoría de pantallas
- Parcial en reports hero (título + slug)
- TN usa wizard steps

## Problemas

- Cambio app = cambio contexto completo (sin breadcrumb retorno)
- Pedidos accesibles desde Ventas y Ecom
- PWA Nivel A reduce menú a 5 apps (`core/pwa_nivel_a.py`)
