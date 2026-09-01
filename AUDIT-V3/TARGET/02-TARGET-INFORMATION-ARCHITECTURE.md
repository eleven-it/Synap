# 02 — Information Architecture Objetivo

**Estado:** COMPLETE | Propuesta basada en capacidades — **no implementar aún**

---

## Principio rector

La navegación **SHOULD** organizarse por **capacidad de negocio**, no por `INSTALLED_APPS`.

```text
Synap (shell)
├── Operaciones          ← stock, inventario, logística
├── Comercial            ← pedidos, clientes, precios, TN
├── Producción           ← MPR, OPT, partes
├── Punto de venta       ← TPV / self-checkout
├── Finanzas             ← contabilidad audit, captura compras, FE AFIP
├── Análisis             ← reports, dashboards, SIA
├── Administración       ← usuarios, empresa, permisos, integraciones
└── Asistente            ← IA (transversal)
```

---

## Mapeo actual → objetivo

| Capacidad objetivo | Apps actuales | Acción IA |
|--------------------|---------------|-----------|
| Operaciones | stock, logistica (parcial) | Consolidar menú stock |
| Comercial | ecom, ventas, tiendanube | **Unificar** pedidos bajo Comercial; ventas presupuestos → sub-sección o rewrite |
| Producción | mpr | Mantener quick-nav MPR |
| Punto de venta | self_checkout | Entrada directa PWA Nivel A |
| Finanzas | contabilidad_audit, compras, fe_afip | Agrupar bajo Finanzas |
| Análisis | reports, sia | Catálogo unificado "Informes" |
| Administración | core/archivo, odoo_migracion | Settings + Archivo merge conceptual |

---

## Profundidad objetivo

| Nivel | Contenido | Max depth |
|-------|-----------|:---------:|
| L1 | Área de capacidad (navbar) | 1 |
| L2 | Sección (sidebar) | 2 |
| L3 | Pantalla lista/dashboard | 3 |
| L4 | Detalle / edición | 4 |

**Regla:** profundidad > 4 requiere justificación (wizard multi-paso OK con breadcrumb).

---

## Duplicaciones a resolver

| Duplicación | Resolución propuesta |
|-------------|---------------------|
| Pedidos Ventas + Ecom | Una entrada "Pedidos" en Comercial |
| Pedido masivo dual | Sub-item único bajo Pedidos |
| Settings vs Archivo usuarios | Una pantalla usuarios en Administración |
| Informe inventario Reports + MPR | Link cruzado; definición única en reports |

---

## Nomenclatura

- **UI en español** para usuarios finales (regla proyecto)
- Términos canónicos: Pedido, Informe, Dashboard, Producción, Stock, Cliente
- Evitar mezcla EN/ES en menú (Reports → Informes, Settings → Configuración)

---

## Breadcrumbs (nuevo estándar)

Toda pantalla L3+ **SHOULD** mostrar:

```text
Área > Sección > Pantalla [> Detalle]
```

Implementación: partial Django reutilizable en `theme/`.

---

*Referencia: `PRODUCT/04-INFORMATION-ARCHITECTURE.md`, `UIUX/03-NAVIGATION-MAP.md`*
