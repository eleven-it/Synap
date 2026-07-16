# Pedidos hub — Lista | Kanban

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales` (+ `ecom-hub-movil-jerarquia-aprobacion`)  
**Ruta:** `/ecom/mayoristapp/pedidos/` (`ecom:mayoristapp_pedidos_hub`)  
**Canon UI:** Tablero de producción MPR (header `slate-800`, viewport flex).  
**Fecha:** 16/07/2026

## Rol

Pantalla **inicial** del módulo Pedidos. Reemplaza el hub solo-KPI. El vendedor ve su trabajo y puede:

- Continuar un **borrador** (pedido simple `EcomCart` o masivo por sucursales)
- Ver PED **enviados / por autorizar / aprobados / anulados**
- Crear **Nuevo** → Simple | Masivo sucursales

## Vistas

| Toggle / breakpoint | Uso |
|---------------------|-----|
| **&lt; lg (móvil)** | Chips de estado + tarjetas apiladas (sin scroll horizontal); tap abre `/mayoristapp/venta/?cod_mov=` |
| **Lista** (≥ lg) | Tabla densa, filtros, paginación |
| **Kanban** (≥ lg) | Columnas por estado (estilo Odoo; sin DnD de estados Admin) |

Preferencia Lista/Kanban: `localStorage` clave `synap_pedidos_hub_vista`.

Con **workflow comercial ON** y subflag aprobación activa, el hub expone cola **Por aprobar** con CTA aprobar/rechazar (permiso `ecom.pedidos.aprobar`, alcance org). Ver [JERARQUIA_COMERCIAL_APROBACION.md](JERARQUIA_COMERCIAL_APROBACION.md).

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
| `ecom.pedidos.ver_todos` | Ver todos los vendedores (alcance org o legacy según master flag) |
| `ecom.pedidos.aprobar` | Aprobar/rechazar cola comercial en hub |
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
- Botón **Actualizar** en el hero: vuelve a pedir el JSON del hub (`urls.api`) sin recargar la página; icono `refresh` con spin mientras `cargando`

## Tarjetas enriquecidas

| Tipo | Título | Campo extra |
|------|--------|-------------|
| Borrador masivo / anulado | `Masivo · {nombre_cliente}` | `meta.nombre_cliente` |
| Borrador carrito simple | `Pedido simple · {nombre_cliente}` | `meta.nombre_cliente` |
| PED confirmado | `PED {nro}` | `sucursal` (domicilio de entrega vía `cliente_datos_adicionales` + `cliente_domicilio`) |

Nombres de cliente: batch `_nombres_clientes` (un SQL). Sucursal: etiqueta `Calle Nro` o `Sucursal #{id}` (misma convención que pedido masivo). Total PED: preferir `ImporteVenta` (bruto); fallback fórmula IVA+percepciones.

Vista **Lista**: columna **Sucursal** entre Documento y Detalle. Vista **Kanban**: línea de sucursal bajo el subtítulo en tarjetas PED.
