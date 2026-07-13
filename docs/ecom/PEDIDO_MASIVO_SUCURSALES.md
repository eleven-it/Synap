# Pedido masivo por sucursales

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales`  
**Ruta (Phase 4):** `/ecom/mayoristapp/pedido-masivo-sucursales/`  
**Canon UI:** Tablero de producción  
**Fecha:** 13/07/2026

## Flujo

1. Elegir cliente (solo con ternas del viajante).  
2. Columnas = `cliente_domicilio` no anulados.  
3. Filas = artículos de marcas asignadas (vendedor, cliente).  
4. Celdas = cantidad en **packs**.  
5. Confirmar → **1 PED por sucursal** con `cliente_datos_adicionales.id_cliente_domicilio`.

## Borrador (Postgres)

Modelos: `EcomPedidoMasivoDraft` + `EcomPedidoMasivoDraftCelda`.

| Estado | Significado |
|--------|-------------|
| `borrador` | Editable; autoguardado |
| `confirmando` | Lock anti doble submit |
| `confirmado` | Lote OK; links a `CodigoMovimiento[]` |
| `archivado` | Descartado al crear otro |

### Resiliencia

- **Cierre / F5:** recuperar desde hub.  
- **Fallo batch:** compensar PED del lote, draft → `borrador` con celdas intactas + `ultimo_error` JSON por sucursal.  
- Nunca vaciar la matriz por error de checkout.

## Permisos

| Key | Uso |
|-----|-----|
| `ecom.pedido_masivo.usar` | Abrir y confirmar matriz |
| `ecom.pedidos.ver` | Ver borradores en hub |

## Endpoints (Phase 4)

| Método | Path | Uso |
|--------|------|-----|
| GET | `/ecom/api/mayoristapp/pedido-masivo/clientes/?q=` | Clientes con ternas del viajante |
| GET | `/ecom/api/mayoristapp/pedido-masivo/sucursales/?id_cliente=` | Columnas `cliente_domicilio` |
| POST | `/ecom/api/mayoristapp/pedido-masivo/abrir/` | Crear/recuperar draft + matriz |
| GET | `/ecom/api/mayoristapp/pedido-masivo/matriz/?draft_id=` | Releer matriz |
| POST | `/ecom/api/mayoristapp/pedido-masivo/celda/` | Autoguardado celda |
| GET | `/ecom/api/mayoristapp/pedido-masivo/articulos/?id_cliente=&q=` | Catálogo filtrado por marcas terna |

UI: `/ecom/mayoristapp/pedido-masivo-sucursales/?draft=<id>`

**Confirmación de lote (1 PED/sucursal):** implementada (Phase 5).

| Método | Path | Uso |
|--------|------|-----|
| POST | `/ecom/api/mayoristapp/pedido-masivo/confirmar/` | Batch + compensación; body `{draft_id, id_punto_venta?}` |

Servicio: `ecom.services.batch_checkout_masivo.confirmar_lote_masivo`.
