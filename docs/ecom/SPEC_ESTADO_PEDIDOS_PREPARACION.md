# Spec — Estado de pedidos (pantalla preparación / logística)

## 1. Alcance

| Origen legado | Synap |
|---------------|--------|
| `mayoristapp/logistica_pantalla_preparacion.php` | Vista web `ecom:mayoristapp_estado_pedidos_preparacion` |
| `mayoristapp/ajax/json_pantalla_pedidos.php` | API `ecom:mayoristapp_logistica_estado_pedidos` |

**Objetivo de negocio:** ofrecer un tablero operativo (tres columnas) para **seguimiento visual** del flujo de pedidos en depósito: qué está **preparado**, qué está **en preparación** (con responsable si existe) y qué está **en remito** pendiente, filtrado por **sucursal**. Sustituye la pantalla tipo TV del PHP para uso en Synap con el mismo patrón de informes (actualizar, exportar, tiempo real, filtros, pantalla completa).

## 2. Rutas

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/ecom/mayoristapp/logistica/estado-pedidos/` | UI Kanban (requiere sesión administraNET + `base_empresa`). |
| GET | `/ecom/api/mayoristapp/logistica/estado-pedidos/?sucursales=1` | Lista `{ sucursales: [ { id_sucursal, nombre_sucursal, domicilio_sucursal } ] }`. |
| GET | `/ecom/api/mayoristapp/logistica/estado-pedidos/?ajax=1&cod_sucursal=<id>` | JSON Kanban (mismas claves que PHP). |

**Catálogo de reportes:** slug `mayoristapp-estado-pedidos-preparacion` → redirección a la vista ecom (`/reports/dashboard/mayoristapp-estado-pedidos-preparacion/`).

## 3. Contrato JSON (paridad PHP)

Respuesta principal:

```json
{
  "en_preparacion": [ { "comprobante": "...", "usuario": "..." } ],
  "preparado": [ { "comprobante": "..." } ],
  "en_remito": [ { "comprobante": "...", "usuario": "..." } ]
}
```

- **preparado:** en el PHP original solo se enviaba `comprobante` por ítem (sin `usuario`). Synap mantiene el mismo contrato.
- **usuario:** texto tipo `Apellido Nombre (cod_usuario)` desde `usuarios` vía `id_usuario_preparacion`; si viene vacío, la UI muestra «Sin asignar».

## 4. SQL (implementación Synap)

Tabla principal: `comp_ped`. Filtro opcional: `CodSucursal = %s` cuando se envía `cod_sucursal`.

1. **En preparación:** `Estado IN ('En preparacion', 'En preparación')` — se incluyen ambas grafías por datos históricos (el PHP antiguo usaba `En preparacion` sin tilde).
2. **Preparado:** `Estado = 'Preparado'`.
3. **En remito:** mismo criterio que PHP: join `rem_ped` / `comp_ped` remito, `rem_ped.Anulado = 'No'`, `pedido.Estado = 'En remito'`, `remito.Estado = 'Pendiente'`, orden por `remito.fecha_control ASC`.

Implementación: `ecom/services/logistica_estado_pedidos_relay.py`.

## 5. UI/UX Synap

Misma línea que otros informes ecom migrados: cabecera gradiente «Foco operativo», botones Actualizar, Exportar Excel (CSV UTF-8), Tiempo real (intervalo según `filters_interval.html`), Mostrar/ocultar filtros, Pantalla completa (`body.reports-fullscreen`). Columnas visuales: **Preparado** | **En preparación** | **En remito** (colores ámbar / cielo / esmeralda).

## 6. Permisos

- API: `EcomMayoristappSessionPermission` (usuario autenticado + `session['user'].base_empresa`).
- Vista web: `MayoristappWebSessionMixin` (misma sesión que el portal mayorista).

## 7. Referencias

- Inventario e ingeniería inversa: `docs/ecom/INVENTARIO_REVERSE_LOGISTICA_PANTALLA_PREPARACION.md`.
- Estados `comp_ped`: `reports/docs/VALIDACION_PEDIDOS_PENDIENTES.md`.
- **Lista de comprobantes en rutas** (`logistica_lista_comprobantes_rutas.php`): se migra como **informe legacy en el módulo Reports** (no como vista ecom); ver `docs/ecom/SPEC_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`.
