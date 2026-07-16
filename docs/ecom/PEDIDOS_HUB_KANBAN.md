# Pedidos hub — Lista | Kanban

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales` (+ `ecom-hub-movil-jerarquia-aprobacion`)  
**Ruta:** `/ecom/mayoristapp/pedidos/` (`ecom:mayoristapp_pedidos_hub`)  
**Canon UI:** Tablero de producción MPR (header `slate-800`, viewport flex).  
**Fecha:** 16/07/2026

## Rol

Pantalla **inicial** del módulo Pedidos. Reemplaza el hub solo-KPI. El vendedor ve su trabajo y puede:

- Continuar un **borrador** (pedido simple `EcomCart` o masivo por sucursales)
- Ver PED **enviados / en curso / entregados-cerrados / anulados** (y cola de aprobación si el workflow lo habilita)
- Buscar por **nro PED, cliente o sucursal** (filtro client-side sobre la ventana cargada)
- Crear **Nuevo** → Simple | Masivo sucursales

## Vistas

| Toggle / breakpoint | Uso |
|---------------------|-----|
| **&lt; lg (móvil)** | Chips de estado + tarjetas apiladas (sin scroll horizontal); tap abre `/mayoristapp/venta/?cod_mov=` |
| **Lista** (≥ lg) | Tabla densa; misma búsqueda que Kanban |
| **Kanban** (≥ lg) | Columnas por estado (estilo Odoo; sin DnD de estados Admin) |

Preferencia Lista/Kanban: `localStorage` clave `synap_pedidos_hub_vista`.

Con **workflow comercial ON** y subflag aprobación activa (`aprobacion_pedidos_activa`), el hub expone columnas **Por autorizar** / **Aprobado** y CTA aprobar/rechazar (permiso `ecom.pedidos.aprobar`, alcance org). Si el master workflow o la aprobación están **off**, esas columnas **no** se muestran. Ver [JERARQUIA_COMERCIAL_APROBACION.md](JERARQUIA_COMERCIAL_APROBACION.md).

## Columnas / estados

| Estado | Visible | Origen |
|--------|---------|--------|
| Borrador | siempre | `EcomCart` con ítems + `EcomPedidoMasivoDraft` BORRADOR |
| Enviado | siempre | PED confirmado (`Pendiente`) o mid-flow sin etapa operativa |
| Por autorizar | solo si aprobación comercial activa | Pendiente aprobación comercial o crédito `No Autorizado` |
| Aprobado | solo si aprobación comercial activa | Autorizado comercialmente, aún no en preparación |
| En curso | siempre | Preparación / preparado / remito / parcial |
| Entregado / Cerrado | siempre | `Facturado`, `Entregado`, `Cerrado` |
| Anulado | siempre | Anulados (ventana reciente) + drafts masivos anulados |

Fechas UI: **dd/MM/yyyy**.

### Prácticas de mercado aplicadas

- Columnas = etapas del flujo; **ocultar etapas irrelevantes** a la config (sin Por autorizar/Aprobado si no hay workflow de aprobación).
- **Lista y Kanban** comparten el mismo dataset y la misma búsqueda.
- Etapa terminal **Entregado / Cerrado** separada del trabajo en curso.
- Búsqueda rápida por identificadores operativos (PED, cliente, sucursal) con contador de resultados.
- Ventana temporal acotada en pipeline (p. ej. 60 días) para no saturar el Kanban.

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

- Template: `ecom/templates/ecom/pedidos_hub.html` (canon tablero slate-800; buscador en hero)
- Pipeline: `ecom/services/pedidos_hub_pipeline.py` (`columnas_hub_visibles`, mapeo `en_curso` / `cerrado`)
- API: `GET /ecom/api/mayoristapp/pedidos/hub/`, `POST .../hub/archivar-draft/`
- Preferencia Lista/Kanban: `localStorage` clave `synap_pedidos_hub_vista`
- Botón **Actualizar** en el hero: vuelve a pedir el JSON del hub (`urls.api`) sin recargar la página; icono `refresh` con spin mientras `cargando`

### Viewport fijo (hero + botones) — 16/07/2026

Misma idea que pedido masivo (`.pm-matrix-viewport`): la página **no** scrollea el body. Clase `.pedidos-hub-viewport` + estilos en `pedidos_page_styles.html`.

| Zona | Comportamiento |
|------|----------------|
| Migas + hero (búsqueda, Lista/Kanban, Actualizar, Nuevo, Depósito) | Fija (`flex-shrink-0`) |
| Kanban (≥ lg) | Scrollport `.pedidos-hub-kanban-scroll` (`min-w-0` + `basis-0` + `overflow-x:auto`); fila `.pedidos-hub-kanban-row` con `width:max-content`; cada etapa `overflow-y` en tarjetas |
| Lista (≥ lg) | `overflow` en el contenedor de tabla |
| Móvil (&lt; lg) | Chips fijos; scroll vertical solo en la lista de tarjetas |

## Tarjetas enriquecidas

| Tipo | Título | Campo extra |
|------|--------|-------------|
| Borrador masivo / anulado | `Masivo · {nombre_cliente}` | `meta.nombre_cliente` |
| Borrador carrito simple | `Pedido simple · {nombre_cliente}` | `meta.nombre_cliente` |
| PED confirmado | `PED {nro}` | `sucursal` (domicilio de entrega vía `cliente_datos_adicionales` + `cliente_domicilio`) |

Nombres de cliente: batch `_nombres_clientes` (un SQL). Sucursal: etiqueta `Calle Nro` o `Sucursal #{id}` (misma convención que pedido masivo). Total PED: preferir `ImporteVenta` (bruto); fallback fórmula IVA+percepciones.

Vista **Lista**: columna **Sucursal** entre Documento y Detalle. Vista **Kanban**: línea de sucursal bajo el subtítulo en tarjetas PED.
