# Índice de especificaciones — mayoristapp (Fase B)

**Objetivo:** una vista por vertical del plan [PLAN_FASES_MAYORISTAPP.md](./PLAN_FASES_MAYORISTAPP.md): qué documento gobierna el “cómo”, qué está implementado en Synap y qué falta para Fase C.

**Relays:** detalle archivo a archivo en [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md).

---

## Tabla maestra

| # | Vertical | Spec principal | Implementación Synap (resumen) | Próximo paso Fase C |
|---|----------|----------------|--------------------------------|----------------------|
| 1 | Fundaciones sesión/permisos | [SPEC_MAYORISTAPP_FUNDACIONES.md](./SPEC_MAYORISTAPP_FUNDACIONES.md) | `login` + `session['user']`; relays asumen `base_empresa` | Poblar `vendedor_a_cargo` y flags PHP si faltan |
| 2 | Catálogo y precios | [SPEC_CATALOGO_RUBRO.md](./SPEC_CATALOGO_RUBRO.md), [SPEC_PRECIOS.md](./SPEC_PRECIOS.md) | Catálogo relays v1; lista-precio + promociones v1 (`precio_relays`); cálculo: `price_calculator` | `relay-art*`, stock completo; paridad fina promos vs PHP |
| 3 | Clientes y domicilios | [SPEC_MAYORISTAPP_CLIENTES.md](./SPEC_MAYORISTAPP_CLIENTES.md) | Subrubros tipo cliente v1; clientes v1 (búsqueda, selección, comprobante, domicilio, contacto JSON, rápido lecturas + alta/edición cliente) | Checkpoint `mayoristapp_clientes` cuando se cierre el vertical; pruebas integración MySQL |
| 4 | Comprobantes | [SPEC_MAYORISTAPP_COMPROBANTES.md](./SPEC_MAYORISTAPP_COMPROBANTES.md) | Listados v1 + sugerencias N° + no-cancelados/resumen + anulación pedido + `comprobante-a-mail` (payload/token); checkpoint `mayoristapp_comprobantes` | SMTP productivo |
| 5 | FE / NC / imputar | [SPEC_MAYORISTAPP_FE_NC.md](./SPEC_MAYORISTAPP_FE_NC.md) | `nota-credito`, `factura-electronica`, `facturas-imputar` v1 (lectura JSON); checkpoint `mayoristapp_fe` | escritura FE/imputación y cruce más profundo con `fe_afip` |
| 6 | Cuenta corriente y recibos | [SPEC_MAYORISTAPP_CTACTE_RECIBOS.md](./SPEC_MAYORISTAPP_CTACTE_RECIBOS.md) | ctacte, cuenta-corriente-pedidos, consumos-resumen v1.1 (motor reglas/promos), recibos v1; checkpoints `mayoristapp_ctacte`, `mayoristapp_recibos` | paridad fina en escenarios edge de negocio (si negocio la exige) |
| 7 | Informes | [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md) §C | Relay GET vendedor/gerencia v1 ampliado (`listarPor` y `tipo` stock, `queInforme` selección/ut/uti, `grafico`) | Paridad fina PHP en DB real + cerrar remanentes `relay-filtros-estadisticas`/`relay-devoluciones` con datasets productivos |
| 8 | Logística y carrito | [SPEC_MAYORISTAPP_LOGISTICA_CARRITO.md](./SPEC_MAYORISTAPP_LOGISTICA_CARRITO.md), [SPEC_ESTADO_PEDIDOS_PREPARACION.md](./SPEC_ESTADO_PEDIDOS_PREPARACION.md) | Pantalla **Estado de pedidos** (Kanban) migrada: vista ecom + API JSON + catálogo reportes; pendientes envío, rutas, geo, jcart | Cerrar relays logísticos restantes + checkpoint `mayoristapp_logistica` |

---

## Checkpoints `EcomMigrationCheckpoint` (Fase C)

Modelo Django: `ecom.models.EcomMigrationCheckpoint` (`module_slug` único, `notes`, `updated_at`).

**Regla:** al dar por **cerrado** un vertical en Fase C, crear o actualizar un registro por `module_slug` (no por cada archivo PHP). Los slugs sugeridos están en [MAYORISTAPP_RELAYS.md](./MAYORISTAPP_RELAYS.md) columna **Checkpoint**.

| `module_slug` (ejemplos) | Vertical |
|---------------------------|----------|
| `mayoristapp_catalogo` | Catálogo (múltiples relays) |
| `mayoristapp_precios` | Precios / promos |
| `mayoristapp_clientes` | Clientes |
| `mayoristapp_comprobantes` | Pedidos, remitos, etc. |
| `mayoristapp_ctacte` | Cuenta corriente |
| `mayoristapp_recibos` | Cobranzas |
| `mayoristapp_fe` | FE / NC |
| `mayoristapp_informes_vn` | Ventas netas relay vendedor |
| `mayoristapp_informes_vn_gerencia` | Ventas netas relay gerencia |
| `mayoristapp_stock` | Stock / existencias |
| `mayoristapp_logistica` | Logística |
| `mayoristapp_jcart_web` / `mayoristapp_jcart_mob` | Carritos |

---

## Referencias generales

- [SPEC.md](./SPEC.md) — arquitectura módulo `ecom`  
- [CHECKLIST_FASES_MAYORISTAPP.md](./CHECKLIST_FASES_MAYORISTAPP.md) — cierre por fase  
- Repo PHP: `git@github.com:licPflores/administraNET-ecom.git`

**Cierre Fase B (documentación):** 2026-03-30.
