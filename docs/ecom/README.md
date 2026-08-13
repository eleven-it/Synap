# Documentación E-commerce / Ventas (ecom)

Documentación del módulo **ecom** en Synap: portal mayorista, pedidos, cobranzas, logística e integraciones.

## Manual de usuario

| Documento | Descripción |
|-----------|-------------|
| [MANUAL_USUARIO_VENTAS.md](MANUAL_USUARIO_VENTAS.md) | **Manual de usuario Ventas** (presupuestos, pedidos, precios, ajustes, objetivos, **crédito Finanzas**, enlace a informes de marcas). Actualizado 07/08/2026. |
| [../reports/MANUAL_USUARIO_REPORTES.md](../reports/MANUAL_USUARIO_REPORTES.md) | **Manual de usuario Reports** (Ventas marcas mensual + Ventas Mensuales Licenciatarios). |
| [manual_usuario_ventas.html](manual_usuario_ventas.html) | **Manual HTML** navegable (generado desde el MD). En la app: **`/ecom/manual/`** (requiere login). Regenerar: `python3 scripts/generar_manuales_html.py`. |
| [CREDITO_PEDIDOS_WORKFLOW.md](CREDITO_PEDIDOS_WORKFLOW.md) | Documentación operativa/técnica del workflow de crédito (flags, permisos, hold, bridge VB6). |

### Botón Ayuda en pantallas

Las pantallas del menú **Ventas** y de **crédito** incluyen un botón **Ayuda** (`includes/btn_manual_ayuda.html`) que abre `/ecom/manual/#<sección>` en una pestaña nueva. Secciones: presupuestos, pedidos-hub, pedido-masivo, vendedor-cliente-marca, precios-terminados, evolucion-precios, ajustes-ventas, asignacion-vendedor, objetivos-venta, **credito-pedidos**, **cola-finanzas**, **politicas-credito**, **plantillas-credito**.

## Índice técnico

Ver [MAYORISTAPP_SPEC_INDICE.md](MAYORISTAPP_SPEC_INDICE.md) y [SPEC.md](SPEC.md) para especificaciones detalladas del portal mayorista.

## Integración Tienda Nube ↔ AdministraNET

| Documento | Descripción |
|-----------|-------------|
| [CHECKLIST_HABILITACION_TIENDANUBE_ADMINISTRANET.md](CHECKLIST_HABILITACION_TIENDANUBE_ADMINISTRANET.md) | Checklist infra, webhooks y **activación ops post-reflote** (ModuleConfig, cron, Celery) |
| [ADR_TIENDANUBE_API_VERSIONING.md](ADR_TIENDANUBE_API_VERSIONING.md) | Versión API fija **2025-03**, URLs y auth |
| [ADR_TIENDANUBE_CONTRATOS_API_2026.md](ADR_TIENDANUBE_CONTRATOS_API_2026.md) | Contratos 2026: `visibility`, `inventory_levels`, HTTP 402, fuera de alcance Price Tables/Kits |
| [TIENDANUBE_REFLOTE_DEUDA_PENDIENTE.md](TIENDANUBE_REFLOTE_DEUDA_PENDIENTE.md) | Deuda pendiente del reflote: Celery, cron, nativos UI, OAuth follow-up |
| [TIENDANUBE_WEBHOOKS_API_2025-03.md](TIENDANUBE_WEBHOOKS_API_2025-03.md) | Endpoints webhook TN y receptor Synap |
| [TIENDANUBE_PEDIDOS_ORDER_PAID.md](TIENDANUBE_PEDIDOS_ORDER_PAID.md) | Pipeline `order/paid` → `comp_ped` + REC |
| [TIENDANUBE_PRECIOS_STOCK.md](TIENDANUBE_PRECIOS_STOCK.md) | Precios finales y stock por depósito TN |
| [TIENDANUBE_DEUDA_TECNICA_P0_P2.md](TIENDANUBE_DEUDA_TECNICA_P0_P2.md) | Deuda técnica histórica P0–P2 |
