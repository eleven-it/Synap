# Pedidos hub — Lista | Kanban

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales`  
**Ruta:** `/ecom/mayoristapp/pedidos/` (`ecom:mayoristapp_pedidos_hub`)  
**Canon UI:** Tablero de producción MPR (header `slate-800`, viewport flex).  
**Fecha:** 13/07/2026

## Rol

Pantalla **inicial** del módulo Pedidos. Reemplaza el hub solo-KPI. El vendedor ve su trabajo y puede:

- Continuar un **borrador** (pedido simple `EcomCart` o masivo por sucursales)
- Ver PED **enviados / por autorizar / aprobados / anulados**
- Crear **Nuevo** → Simple | Masivo sucursales

## Vistas

| Toggle | Uso |
|--------|-----|
| **Lista** | Tabla densa, filtros, paginación |
| **Kanban** | Columnas por estado (estilo Odoo; sin DnD de estados Admin) |

Preferencia Lista/Kanban: `localStorage` o sesión.

## Columnas / estados

| Estado | Origen |
|--------|--------|
| Borrador | `EcomCart` con ítems + `EcomPedidoMasivoDraft` BORRADOR |
| Enviado | PED confirmado reciente |
| Por autorizar | PED pendiente autorización |
| Aprobado | Autorizado / en preparación |
| Anulado | Anulados (ventana reciente) |

Fechas UI: **dd/MM/yyyy**.

## Permisos

| Key | Uso |
|-----|-----|
| `ecom.pedidos.ver` | Ver hub |
| `ecom.pedidos.ver_todos` | Ver todos los vendedores |
| `ecom.pedido_masivo.usar` | CTA / abrir masivo |
| `ecom.pedidos.crear` / `ecom.carrito.editar` | Pedido simple |

## Recuperación de borrador

1. Tarjeta en Borrador → Continuar.
2. Nuevo con borrador activo → modal Continuar vs Archivar y crear (nunca pisar en silencio).
3. Borrador con `ultimo_error` → badge “Error al confirmar”; datos intactos.

## Implementación (Phase 3)

- Template: `ecom/templates/ecom/pedidos_hub.html` (canon tablero slate-800)
- Pipeline: `ecom/services/pedidos_hub_pipeline.py`
- API: `GET /ecom/api/mayoristapp/pedidos/hub/`, `POST .../hub/archivar-draft/`
- Preferencia Lista/Kanban: `localStorage` clave `synap_pedidos_hub_vista`
