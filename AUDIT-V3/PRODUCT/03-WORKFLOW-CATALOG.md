# 03 — Catálogo de Workflows

**Estado:** COMPLETE | Workflows críticos reconstruidos desde código

## WF-01: Login y selección empresa

| Campo | Valor |
|-------|-------|
| Intent | Acceder al sistema |
| Entry | `GET/POST /login/` |
| Steps | elegir empresa → usuario/password → validate AN → bootstrap session |
| Success | redirect `/core/dashboard/` |
| Failure | rate limit, credenciales inválidas |
| Evidence | `login/views.py:41-111`, `session_bootstrap.py` |

## WF-02: Crear pedido mayorista (ecom)

| Intent | Comprar como mayorista |
| Entry | `/ecom/mayoristapp/` → catálogo |
| Steps | buscar artículo → carrito → checkout → aprobación (si crédito) → INSERT comp_ped |
| Screens | portal, carrito, hub kanban |
| APIs | checkout services, hub API |
| Failure | stock insuficiente, crédito rechazado |
| Evidence | `mayorista_checkout_service.py`, `pedido_gestion_views.py` |

## WF-03: Pedido masivo sucursales

| Intent | Cargar matriz Excel multi-sucursal |
| Entry | `/ecom/mayoristapp/pedido-masivo-sucursales/` |
| Steps | descargar plantilla → completar → importar → revisar matriz → confirmar |
| Artifact | `.xlsx` plantilla (`pedido_masivo_import.py`) |
| Evidence | `pedido_masivo_views.py` |

## WF-04: Producción OPT (MPR wizard)

| Intent | Planificar y ejecutar producción |
| Entry | `/mpr/wizard/` |
| Steps | crear OPT → confirmar → OPP → cierre → stock movements |
| Screens | wizard, opt_list, opt_detail, tablero |
| Evidence | `mpr/views.py:972+`, `mpr/services.py` |

## WF-05: Parte operario móvil

| Intent | Registrar producción del turno |
| Entry | `/mpr/parte-produccion/` (mobile) |
| Steps | seleccionar turno → cargar cantidades → enviar parte |
| Permission | `mpr.parte_operario` |
| Evidence | `mpr/templates/mpr/mobile/parte_operario.html` |

## WF-06: Venta TPV self-checkout

| Intent | Vender en kiosco |
| Entry | `/self_checkout/kiosco/<id>/` |
| Steps | scan artículos → pagar → confirmar → stock + cuentacliente + resumen_venta_cv |
| Artifact | ticket print `ticket_print.html` |
| Evidence | `confirmation_service.py` |

## WF-07: Consultar dashboard reportes

| Intent | Analizar indicadores |
| Entry | `/reports/` → catálogo → `/reports/dashboard/<slug>/` |
| Steps | aplicar filtros → ejecutar query → widgets render |
| Modes | declarative-v1 vs legacy JS |
| Evidence | `dashboard_detail.html`, `widget_engine.js` |

## WF-08: Inventario físico

| Intent | Contar y ajustar stock |
| Entry | `/stock/inventario-fisico/` |
| Steps | crear campaña → conteo móvil (QR) → autorizar ajuste |
| Mobile | **MOBILE CRITICAL** |
| Evidence | `stock/conteo/mobile/` |

## WF-09: Auditoría contable

| Intent | Validar/corregir asientos |
| Entry | `/contabilidad/auditoria/` |
| Steps | definir política → ejecutar corrida → revisar hallazgos → dry-run/apply |
| Export | xlsx/csv (`contabilidad_audit/services/export.py`) |

## WF-10: Sync Tienda Nube

| Intent | Mantener catálogo/pedidos sincronizados |
| Entry | TN dashboard |
| Steps | configurar mappings → webhook/sync → adminet_service writes |
| Pattern | outbox + webhooks |
| Evidence | `tiendanube_administranet/` |
