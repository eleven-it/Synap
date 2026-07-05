# Mapeo API REST v1 — comprobantes pedidos

**Change:** `ecom-migracion-completa` (F0 piloto)

## relay-pedidos.php → Synap

| Legacy | REST v1 canónico |
|--------|------------------|
| `POST /ecom/api/mayoristapp/comprobantes/pedidos/?ajax=1` | `POST /ecom/api/v1/mayoristapp/comprobantes/pedidos/` |
| `GET .../comprobantes/sugerencias-nro/?ajax=1&tipo=PED` | `GET /ecom/api/v1/mayoristapp/comprobantes/pedidos/sugerencias-numero/?q=` |

Legacy responde con header `Deprecation: true` y `Link: </ecom/api/v1/...>; rel="successor-version"`.

## Cuerpo POST — mapeo campos

| REST v1 (snake_case) | Relay / PHP (camelCase) |
|----------------------|-------------------------|
| `campo_busca` | `campoBusca` |
| `fecha_desde` | `fechaDesde` |
| `fecha_hasta` | `fechaHasta` |
| `numero_comp` | `numeroComp` |
| `estado_pedido` | `estadoPedido` |
| `tipo_pedido` | `tipoPedido` |
| `lista_ped` | `listaPed` |
| `filtra_vendedor` | `filtraVendedor` |
| `vendedor` | `vendedor` |
| `page_size` / `limit` | `limit` |

## Consumidor UI (F1)

| Pantalla | URL | API |
|----------|-----|-----|
| Pedidos del vendedor | `GET /ecom/mayoristapp/pedidos-vendedor/` | `POST` v1 listado (sin `ajax=1`) |

Presupuestos sigue en legacy hasta migración v1 en change posterior.

```json
{
  "ok": true,
  "page": 1,
  "page_size": 500,
  "total": 12,
  "results": [ "... filas igual que servicio legacy ..." ]
}
```

Error:

```json
{ "ok": false, "error": "mensaje en español", "code": "sin_base_empresa" }
```

## Permisos

- v1: `ecom.comprobantes.ver` + sesión `base_empresa`
- legacy: `EcomMayoristappSessionPermission` (compatibilidad)

## Próximos verticales F1

Replicar patrón en presupuestos, remitos, clientes, ctacte, etc.
